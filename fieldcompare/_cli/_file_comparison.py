"""Class to compare two files using the CLI options"""

from typing import Union, List, Callable, TextIO, TypeVar, Optional
from dataclasses import dataclass
from io import StringIO

from .._array import as_array, has_floats
from ..protocols import Field, FieldData, FieldDataSequence, Predicate
from ..predicates import FuzzyEquality, ExactEquality
from .._common import _default_base_tolerance
from .._format import (
    as_success,
    as_error,
    as_warning,
    highlighted
)

from ..tabular import read as read_table
from ..mesh import (
    read as read_mesh,
    read_sequence as read_mesh_sequence,
    permutations as mesh_permutations
)

from .._comparisons import (
    FieldDataComparison,
    FieldComparisonSuite,
    FieldComparisonResult,
    FieldComparisonStatus
)

from ._logger import CLILogger
from ._deduce_domain import deduce_file_type, FileType, DomainType
from ._test_suite import TestSuite, Test, TestResult


@dataclass
class FileComparisonOptions:
    ignore_missing_result_fields: bool = False
    ignore_missing_reference_fields: bool = False
    ignore_missing_sequence_steps: bool = False
    force_sequence_comparison: bool = False
    relative_tolerances: Callable[[str], float] = lambda _: _default_base_tolerance()
    absolute_tolerances: Callable[[str], float] = lambda _: _default_base_tolerance()
    field_inclusion_filter: Callable[[str], bool] = lambda _: True
    field_exclusion_filter: Callable[[str], bool] = lambda _: False
    disable_unconnected_points_removal: bool = False
    disable_mesh_reordering: bool = False


class FileComparison:
    def __init__(self,
                 opts: FileComparisonOptions,
                 logger: CLILogger) -> None:
        self._opts = opts
        self._logger = logger

    def __call__(self, res_file: str, ref_file: str) -> TestSuite:
        res_file_type = deduce_file_type(res_file)
        ref_file_type = deduce_file_type(ref_file)
        if res_file_type != ref_file_type:
            return _make_test_suite(
                tests=[],
                result=TestResult.error,
                shortlog="Non-matching file types: '{ref_file_type}' / '{res_file_type}"
            )
        if res_file_type.domain_type == DomainType.unknown:
            return _make_test_suite(
                tests=[],
                result=TestResult.error,
                shortlog="Unsupported file type"
            )
        return self._compare_files(res_file, ref_file, res_file_type)

    def _compare_files(self, res_file: str, ref_file: str, file_type: FileType) -> TestSuite:
        if file_type.domain_type == DomainType.mesh:
            return self._run_mesh_file_comparison(res_file, ref_file, file_type)
        if file_type.domain_type == DomainType.table:
            return self._run_tabular_data_file_comparison(res_file, ref_file, file_type)
        raise NotImplementedError("Unknown file type: '{file_type}'")

    def _run_mesh_file_comparison(self,
                                  res_file: str,
                                  ref_file: str,
                                  file_type: FileType) -> TestSuite:
        if file_type.is_sequence:
            return self._run_file_comparison(
                res_file, ref_file, "mesh sequence",
                read_function=read_mesh_sequence,
                comparison_function=self._run_mesh_sequence_comparison
            )
        else:
            return self._run_file_comparison(
                res_file, ref_file, "mesh",
                read_function=read_mesh,
                comparison_function=self._run_mesh_comparison
            )

    def _run_tabular_data_file_comparison(self,
                                          res_file: str,
                                          ref_file: str,
                                          file_type: FileType) -> TestSuite:
        return self._run_file_comparison(
            res_file, ref_file, "table",
            read_function=read_table,
            comparison_function=lambda *args, **kwargs: self._to_test_suite(
                self._run_field_data_comparison(*args, **kwargs)
            )
        )

    _T = TypeVar("_T")
    def _run_file_comparison(self,
                             res_file: str,
                             ref_file: str,
                             domain: str,
                             read_function: Callable[[str], _T],
                             comparison_function: Callable[[_T, _T], TestSuite]) -> TestSuite:
        def _read(file: str):
            self._logger.log(f"Reading {domain} from '{highlighted(file)}'\n", verbosity_level=1)
            return read_function(file)

        try:
            res_fields = _read(res_file)
        except IOError as e:
            return _make_test_suite(
                tests=[],
                result=TestResult.error,
                shortlog=f"Error reading fields from '{res_file}': {e}"
            )

        try:
            ref_fields = _read(ref_file)
        except IOError as e:
            return _make_test_suite(
                tests=[],
                result=TestResult.error,
                shortlog=f"Error reading reference file '{res_file}': {e}"
            )
        return comparison_function(res_fields, ref_fields)

    def _run_mesh_sequence_comparison(self,
                                      res_sequence: FieldDataSequence,
                                      ref_sequence: FieldDataSequence) -> TestSuite:
        num_steps_check: Optional[TestResult] = None
        num_steps_check_fail_msg = "Mesh sequences have differing lengths"
        if res_sequence.number_of_steps != ref_sequence.number_of_steps:
            if not self._opts.ignore_missing_sequence_steps:
                num_steps_check = TestResult.failed
                self._logger.log(f"{self._status_string(TestResult.error)}: {num_steps_check_fail_msg}")
                if not self._opts.force_sequence_comparison:
                    return _make_test_suite([], TestResult.failed, num_steps_check_fail_msg)
            else:
                self._logger.log(
                    f"{as_warning('Warning')}: {num_steps_check_fail_msg}, comparing only common steps\n"
                )

        def _merge_test_suites(s1: TestSuite, s2: TestSuite, i: int) -> TestSuite:
            def _merged_result(r1: Optional[TestResult], r2: Optional[TestResult]) -> Optional[TestResult]:
                if any(r == TestResult.failed for r in [r1, r2]): return TestResult.failed
                if any(r == TestResult.error for r in [r1, r2]): return TestResult.error
                if any(r == TestResult.skipped for r in [r1, r2]): return TestResult.skipped
                return None
            return _make_test_suite(
                tests=list(s1) + list(s2),
                result=_merged_result(s1.result, s2.result),
                shortlog=s1.shortlog + (
                    f"; {s2.shortlog}" if s1.shortlog else f"{s2.shortlog}"
                )
            )

        suite = _make_test_suite([], num_steps_check, "")
        num_steps = min(res_sequence.number_of_steps, ref_sequence.number_of_steps)
        for idx, (res_step, ref_step) in enumerate(zip(res_sequence, ref_sequence)):
            self._logger.log(f"Comparing step {idx} of {num_steps}\n", verbosity_level=1)
            sub_suite = self._run_mesh_comparison(res_step, ref_step)
            suite = _merge_test_suites(suite, sub_suite, idx)
        return suite

    def _set_mesh_tolerances(self, fields: FieldData) -> None:
        fields.domain.set_tolerances(
            abs_tol=self._opts.absolute_tolerances("domain"),
            rel_tol=self._opts.relative_tolerances("domain")
        )

    def _run_mesh_comparison(self, res_fields: FieldData, ref_fields: FieldData) -> TestSuite:
        self._set_mesh_tolerances(res_fields)
        self._set_mesh_tolerances(ref_fields)
        suite = self._run_field_data_comparison(res_fields, ref_fields)
        if suite.domain_equality_check:
            return self._to_test_suite(suite)

        if self._opts.disable_mesh_reordering:
            msg = "Non-reordered meshes have compared unequal"
            self._logger.log(f"{self._status_string(TestResult.failed)}: {msg}")
            return _make_test_suite([], TestResult.failed, shortlog=msg)

        self._logger.log(
            "Meshes did not compare equal. Retrying with sorted points...\n",
            verbosity_level=1
        )
        def _permute(mesh_fields):
            if not self._opts.disable_unconnected_points_removal:
                mesh_fields = mesh_fields.permuted(mesh_permutations.remove_unconnected_points)
            return mesh_fields.permuted(mesh_permutations.sort_points)
        res_fields = _permute(res_fields)
        ref_fields = _permute(ref_fields)
        suite = self._run_field_data_comparison(res_fields, ref_fields)
        if suite.domain_equality_check:
            return self._to_test_suite(suite)

        self._logger.log(
            "Meshes did not compare equal. Retrying with sorted cells...\n",
            verbosity_level=1
        )
        res_fields = res_fields.permuted(mesh_permutations.sort_cells)
        ref_fields = ref_fields.permuted(mesh_permutations.sort_cells)
        suite = self._run_field_data_comparison(res_fields, ref_fields)
        if suite.domain_equality_check:
            return self._to_test_suite(suite)

        msg = "Fields defined on different meshes"
        self._logger.log(f"{self._status_string(TestResult.failed)}: {msg}")
        return _make_test_suite([], TestResult.failed, shortlog="Fields defined on different meshes")

    def _run_field_data_comparison(self,
                                   result: FieldData,
                                   reference: FieldData) -> FieldComparisonSuite:
        return FieldDataComparison(
            result, reference,
            self._opts.field_inclusion_filter, self._opts.field_exclusion_filter
        )(
            predicate_selector=lambda res, ref: self._select_predicate(res, ref),
            fieldcomp_callback=lambda comp: self._stream_field_comparison_report(comp, self._logger)
        )

    def _select_predicate(self, res_field: Field, ref_field: Field) -> Predicate:
        if has_floats(as_array(res_field.values)) or has_floats(as_array(ref_field.values)):
            return FuzzyEquality(
                abs_tol=self._opts.absolute_tolerances(res_field.name),
                rel_tol=self._opts.relative_tolerances(res_field.name)
            )
        else:
            return ExactEquality()

    def _stream_field_comparison_report(self,
                                        result: FieldComparisonResult,
                                        device: Union[CLILogger, TextIO]) -> None:
        def _log(message: str, verbosity_level: int) -> None:
            if isinstance(device, CLILogger):
                device.log(f"{message}\n", verbosity_level)
            else:
                device.write(f"{message}\n")

        _log(
            message=_get_indented(
                f"Comparing the field '{highlighted(result.name)}': "
                f"{self._status_string(self._parse_status(result.status))}",
                indentation_level=1
            ),
            verbosity_level=1
        )
        _log(
            message=_get_indented(
                f"Report: {result.report if result.report else 'n/a'}\n"
                f"Predicate: {result.predicate if result.predicate else 'n/a'}",
                indentation_level=2
            ),
            verbosity_level=2
        )

    def _to_test_suite(self, suite: FieldComparisonSuite) -> TestSuite:
        return TestSuite([self._to_test(c) for c in suite])

    def _to_test(self, comp_result: FieldComparisonResult) -> Test:
        def _get_stdout() -> str:
            stream = StringIO()
            self._stream_field_comparison_report(comp_result, stream)
            return stream.getvalue()

        shortlog = comp_result.report
        if comp_result.status == FieldComparisonStatus.missing_reference:
            shortlog = "missing reference field"
        if comp_result.status == FieldComparisonStatus.missing_source:
            shortlog = "missing source field"
        return Test(
            name=comp_result.name,
            result=self._parse_status(comp_result.status),
            shortlog=shortlog,
            stdout=_get_stdout(),
            cpu_time=comp_result.cpu_time
        )

    def _parse_status(self, status: FieldComparisonStatus) -> TestResult:
        if status == FieldComparisonStatus.passed: return TestResult.passed
        if status == FieldComparisonStatus.failed: return TestResult.failed
        if status == FieldComparisonStatus.error: return TestResult.error
        if status == FieldComparisonStatus.missing_reference \
            and not self._opts.ignore_missing_reference_fields:
            return TestResult.failed
        if status == FieldComparisonStatus.missing_source \
            and not self._opts.ignore_missing_result_fields:
            return TestResult.failed
        return TestResult.skipped

    def _status_string(self, status: TestResult) -> str:
        if status == TestResult.passed:
            return as_success("PASSED")
        if status in [TestResult.failed, TestResult.error]:
            return as_error("FAILED")
        return as_warning("SKIPPED")


def _get_indented(message: str, indentation_level: int = 0) -> str:
    if indentation_level > 0:
        lines = message.rstrip("\n").split("\n")
        lines = [" " + "  "*(indentation_level-1) + f"-- {line}" for line in lines]
        message = "\n".join(lines)
    return message

def _make_test_suite(tests: List[Test],
                     result: Optional[TestResult],
                     shortlog: str = "") -> TestSuite:
    return TestSuite(
        tests=tests,
        result=result,
        shortlog=shortlog
    )
