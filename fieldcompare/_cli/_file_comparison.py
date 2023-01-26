# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Class to compare two files using the CLI options"""

from pathlib import Path
from typing import Union, List, Callable, Optional
from dataclasses import dataclass

from ..predicates import DefaultEquality
from ..protocols import DynamicTolerance
from ..io import read, read_as

from .._common import _default_base_tolerance
from .._format import as_success, as_error, as_warning, highlighted

from .._field_data_comparison import (
    FieldDataComparator,
    FieldComparisonSuite,
    FieldComparison,
    FieldComparisonStatus,
    field_comparison_report,
)
from ..mesh import MeshFieldsComparator

from ._logger import CLILogger
from ._common import FileTypeMap
from ._test_suite import TestSuite, TestResult, TestStatus

from .. import protocols
from ..mesh import protocols as mesh_protocols


Tolerance = Union[float, DynamicTolerance]


@dataclass
class FileComparisonOptions:
    ignore_missing_source_fields: bool = False
    ignore_missing_reference_fields: bool = False
    ignore_missing_sequence_steps: bool = False
    force_sequence_comparison: bool = False
    relative_tolerances: Callable[[str], Optional[Tolerance]] = lambda _: _default_base_tolerance()
    absolute_tolerances: Callable[[str], Optional[Tolerance]] = lambda _: 0.0
    field_inclusion_filter: Callable[[str], bool] = lambda _: True
    field_exclusion_filter: Callable[[str], bool] = lambda _: False
    disable_unconnected_points_removal: bool = False
    disable_mesh_space_dimension_matching: bool = False
    disable_mesh_reordering: bool = False
    file_type_map: FileTypeMap = FileTypeMap()


class FileComparison:
    def __init__(self, opts: FileComparisonOptions, logger: CLILogger) -> None:
        self._opts = opts
        self._logger = logger

    def __call__(self, res_file: str, ref_file: str) -> TestSuite:
        try:
            res_fields = self._read(res_file)
            ref_fields = self._read(ref_file)
        except IOError:
            return _make_test_suite(
                tests=[], status=TestStatus.error, name=_suite_name(res_file), shortlog="Error during field reading"
            )
        return self._compare_fields(res_fields, ref_fields).with_overridden(name=_suite_name(res_file))

    def _read(self, filename: str) -> Union[protocols.FieldData, protocols.FieldDataSequence]:
        try:
            file_type_with_opts = self._opts.file_type_map(filename)
            log_suffix = f" as '{file_type_with_opts[0]}'" if file_type_with_opts is not None else ""
            self._logger.log(f"Reading '{highlighted(filename)}'{log_suffix}\n", verbosity_level=1)
            return (
                read(filename)
                if file_type_with_opts is None
                else read_as(file_type_with_opts[0], filename, **file_type_with_opts[1])
            )
        except IOError as e:
            self._logger.log(f"Error: '{e}'\n", verbosity_level=1)
            raise IOError(e)

    def _compare_fields(
        self,
        res_fields: Union[protocols.FieldData, protocols.FieldDataSequence],
        ref_fields: Union[protocols.FieldData, protocols.FieldDataSequence],
    ) -> TestSuite:
        if isinstance(res_fields, protocols.FieldData) and isinstance(ref_fields, protocols.FieldData):
            return self._compare_field_data(res_fields, ref_fields)
        elif isinstance(res_fields, protocols.FieldDataSequence) and isinstance(
            ref_fields, protocols.FieldDataSequence
        ):
            return self._compare_field_sequences(res_fields, ref_fields)

        def _is_unknown(fields) -> bool:
            return not isinstance(fields, protocols.FieldData) and not isinstance(fields, protocols.FieldDataSequence)

        if any(_is_unknown(f) for f in [res_fields, ref_fields]):
            raise ValueError("Unknown data type (supported are 'FieldData' / 'FieldDataSequence')")
        raise ValueError("Cannot compare sequences against field data")

    def _compare_field_sequences(
        self, res_sequence: protocols.FieldDataSequence, ref_sequence: protocols.FieldDataSequence
    ) -> TestSuite:
        num_steps_check: Optional[TestStatus] = None
        num_steps_check_fail_msg = "Sequences have differing lengths"
        if res_sequence.number_of_steps != ref_sequence.number_of_steps:
            if not self._opts.ignore_missing_sequence_steps:
                num_steps_check = TestStatus.failed
                self._logger.log(f"{num_steps_check_fail_msg}\n")
                if not self._opts.force_sequence_comparison:
                    return _make_test_suite([], TestStatus.failed, shortlog=num_steps_check_fail_msg)
            else:
                self._logger.log(f"{as_warning('Warning')}: {num_steps_check_fail_msg}, comparing only common steps\n")

        def _merge_test_suites(s1: TestSuite, s2: TestSuite, i: int) -> TestSuite:
            def _merged_result(r1: Optional[TestStatus], r2: Optional[TestStatus]) -> Optional[TestStatus]:
                if any(r == TestStatus.failed for r in [r1, r2]):
                    return TestStatus.failed
                if any(r == TestStatus.error for r in [r1, r2]):
                    return TestStatus.error
                if any(r == TestStatus.skipped for r in [r1, r2]):
                    return TestStatus.skipped
                return None

            return _make_test_suite(
                tests=list(s1) + list(s2),
                status=_merged_result(s1.status, s2.status),
                shortlog=s1.shortlog + (f"; {s2.shortlog}" if s1.shortlog else f"{s2.shortlog}"),
            )

        suite = _make_test_suite([], num_steps_check, "")
        num_steps = min(res_sequence.number_of_steps, ref_sequence.number_of_steps)
        for idx, (res_step, ref_step) in enumerate(zip(res_sequence, ref_sequence)):
            self._logger.log(f"Comparing step {idx} of {num_steps}\n", verbosity_level=1)
            sub_suite = self._compare_field_data(res_step, ref_step)
            suite = _merge_test_suites(suite, sub_suite, idx)
        return suite

    def _compare_field_data(self, res_fields: protocols.FieldData, ref_fields: protocols.FieldData) -> TestSuite:
        if isinstance(res_fields, mesh_protocols.MeshFields) and isinstance(ref_fields, mesh_protocols.MeshFields):
            return self._compare_mesh_field_data(res_fields, ref_fields)
        suite = self._run_field_data_comparison(res_fields, ref_fields)
        if suite.domain_equality_check:
            return self._to_test_suite(suite)
        msg = "Domains have compared unequal"
        self._logger.log(f"{msg}\n")
        return _make_test_suite([], TestStatus.failed, shortlog=msg)

    def _compare_mesh_field_data(
        self, res_fields: mesh_protocols.MeshFields, ref_fields: mesh_protocols.MeshFields
    ) -> TestSuite:
        self._set_mesh_tolerances(res_fields)
        self._set_mesh_tolerances(ref_fields)
        if self._opts.disable_mesh_reordering:
            suite = self._run_field_data_comparison(res_fields, ref_fields)
            if suite.domain_equality_check:
                return self._to_test_suite(suite)
            msg = "Non-reordered meshes have compared unequal"
            self._logger.log(f"{msg}\n")
            return _make_test_suite([], TestStatus.failed, shortlog=msg)

        suite = self._run_mesh_fields_comparison(res_fields, ref_fields)
        if suite.domain_equality_check:
            return self._to_test_suite(suite)

        msg = "Fields defined on different meshes"
        self._logger.log(f"{msg}\n")
        return _make_test_suite([], TestStatus.failed, shortlog=msg)

    def _run_mesh_fields_comparison(
        self, result: mesh_protocols.MeshFields, reference: mesh_protocols.MeshFields
    ) -> FieldComparisonSuite:
        return self._invoke_comparator(
            MeshFieldsComparator(
                result,
                reference,
                disable_mesh_reordering=self._opts.disable_mesh_reordering,
                disable_orphan_point_removal=self._opts.disable_unconnected_points_removal,
                disable_space_dimension_matching=self._opts.disable_mesh_space_dimension_matching,
                field_inclusion_filter=self._opts.field_inclusion_filter,
                field_exclusion_filter=self._opts.field_exclusion_filter,
            ),
            reordering_callback=lambda msg: self._logger.log(f"{msg}\n"),
        )

    def _run_field_data_comparison(
        self, result: protocols.FieldData, reference: protocols.FieldData
    ) -> FieldComparisonSuite:
        return self._invoke_comparator(
            FieldDataComparator(result, reference, self._opts.field_inclusion_filter, self._opts.field_exclusion_filter)
        )

    def _invoke_comparator(self, comparator, **kwargs) -> FieldComparisonSuite:
        class Callback:
            def __init__(self, logger: CLILogger) -> None:
                self._logger = logger

            def __call__(self, result: FieldComparison) -> None:
                if self._logger.verbosity_level == 0:
                    return
                if result and self._logger.verbosity_level == 1:
                    return
                msg = field_comparison_report(result, verbosity=max(1, self._logger.verbosity_level - 1))
                self._logger.log(f"{msg}\n")

        return comparator(
            predicate_selector=lambda res, ref: self._select_predicate(res, ref),
            fieldcomp_callback=Callback(logger=self._logger),
            **kwargs,
        )

    def _set_mesh_tolerances(self, fields: protocols.FieldData) -> None:
        fields.domain.set_tolerances(
            abs_tol=self._opts.absolute_tolerances("domain"), rel_tol=self._opts.relative_tolerances("domain")
        )

    def _select_predicate(self, res_field: protocols.Field, ref_field: protocols.Field) -> protocols.Predicate:
        abs_tol = self._opts.absolute_tolerances(res_field.name)
        rel_tol = self._opts.relative_tolerances(res_field.name)
        return DefaultEquality(
            abs_tol=abs_tol if abs_tol is not None else 0.0,
            rel_tol=rel_tol if rel_tol is not None else _default_base_tolerance(),
        )

    def _to_test_suite(self, suite: FieldComparisonSuite) -> TestSuite:
        return TestSuite([self._to_test_result(c) for c in suite])

    def _to_test_result(self, comp_result: FieldComparison) -> TestResult:
        def _get_stdout() -> str:
            return field_comparison_report(comp_result, verbosity=100)

        shortlog = comp_result.report
        if comp_result.status == FieldComparisonStatus.missing_reference:
            shortlog = "missing reference field"
            stdout = shortlog
        elif comp_result.status == FieldComparisonStatus.missing_source:
            shortlog = "missing source field"
            stdout = shortlog
        elif comp_result.status == FieldComparisonStatus.filtered:
            shortlog = "filtered out by given wildcard patterns"
            stdout = shortlog
        else:
            stdout = _get_stdout()

        return TestResult(
            name=comp_result.name,
            status=self._parse_status(comp_result.status),
            shortlog=shortlog,
            stdout=stdout,
            cpu_time=comp_result.cpu_time,
        )

    def _parse_status(self, status: FieldComparisonStatus) -> TestStatus:
        if status == FieldComparisonStatus.passed:
            return TestStatus.passed
        if status == FieldComparisonStatus.failed:
            return TestStatus.failed
        if status == FieldComparisonStatus.error:
            return TestStatus.error
        if status == FieldComparisonStatus.missing_reference and not self._opts.ignore_missing_reference_fields:
            return TestStatus.failed
        if status == FieldComparisonStatus.missing_source and not self._opts.ignore_missing_source_fields:
            return TestStatus.failed
        return TestStatus.skipped

    def _status_string(self, status: TestStatus) -> str:
        if status == TestStatus.passed:
            return as_success("PASSED")
        if status in [TestStatus.failed, TestStatus.error]:
            return as_error("FAILED")
        return as_warning("SKIPPED")


def _make_test_suite(
    tests: List[TestResult], status: Optional[TestStatus], name: Optional[str] = None, shortlog: str = ""
) -> TestSuite:
    return TestSuite(name=name, tests=tests, status=status, shortlog=shortlog)


def _suite_name(filename: str) -> str:
    path = Path(filename)
    if len(path.parts) == 1:
        return filename
    return str(Path(*path.parts[1:]))
