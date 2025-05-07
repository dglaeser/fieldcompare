# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Class to compare two files using the CLI options"""

from __future__ import annotations
from pathlib import Path
from typing import Callable
from dataclasses import dataclass

from ..predicates import DefaultEquality
from ..protocols import DynamicTolerance
from ..io import read, read_as, write

from .._common import _default_base_tolerance
from .._format import as_success, as_error, as_warning, highlighted

from .._field_data_comparison import (
    FieldDataComparator,
    FieldComparisonSuite,
    FieldComparison,
    FieldComparisonStatus,
    FieldComparisonResult,
    field_comparison_report,
)
from ..mesh import MeshFieldsComparator, sort

from ._logger import CLILogger
from ._common import FileTypeMap
from ._test_suite import TestSuite, TestResult, TestStatus

from .. import protocols
from ..mesh import protocols as mesh_protocols


def _default_base_tolerance_callable(*_):
    return _default_base_tolerance()


def _default_abs_tolerance_callable(*_):
    return 0.0


def _always_true_callable(*_):
    return True


def _always_false_callable(*_):
    return False


@dataclass
class FileComparisonOptions:
    ignore_missing_source_fields: bool = False
    ignore_missing_reference_fields: bool = False
    ignore_missing_sequence_steps: bool = False
    force_sequence_comparison: bool = False
    relative_tolerances: Callable[[str], float | DynamicTolerance | None] = _default_base_tolerance_callable
    absolute_tolerances: Callable[[str], float | DynamicTolerance | None] = _default_abs_tolerance_callable
    field_inclusion_filter: Callable[[str], bool] = _always_true_callable
    field_exclusion_filter: Callable[[str], bool] = _always_false_callable
    disable_unconnected_points_removal: bool = False
    disable_mesh_space_dimension_matching: bool = False
    disable_mesh_reordering: bool = False
    file_type_map: FileTypeMap = FileTypeMap()


class FileComparison:
    def __init__(self, opts: FileComparisonOptions, logger: CLILogger, write_diff: bool = False) -> None:
        self._opts = opts
        self._logger = logger
        self._write_diff = write_diff

    def __call__(self, res_file: str, ref_file: str) -> TestSuite:
        try:
            res_fields = self._read(res_file)
            ref_fields = self._read(ref_file)
        except IOError:
            return _make_test_suite(
                tests=[], status=TestStatus.error, name=_suite_name(res_file), shortlog="Error during field reading"
            )
        return self._compare_fields(res_fields, ref_fields, self._get_diff_filename(res_file)).with_overridden(
            name=_suite_name(res_file)
        )

    def _write_diff_file(self, diff_basefilename: str, res_fields, ref_fields):
        if (
            isinstance(res_fields, mesh_protocols.MeshFields)
            and isinstance(ref_fields, mesh_protocols.MeshFields)
            and not res_fields.domain.equals(ref_fields.domain)
            and not self._opts.disable_mesh_reordering
        ):
            self._logger.log("Sorting mesh fields for diff output\n", verbosity_level=2)
            res_fields = sort(res_fields)
            ref_fields = sort(ref_fields)

        try:
            diff = res_fields.diff_to(ref_fields)
            diff_filename = write(diff, diff_basefilename)
            self._logger.log(f"Wrote diff into '{highlighted(diff_filename)}'\n", verbosity_level=1)
        except Exception as e:
            self._logger.log(f"Error when computing diff: '{e}'")

    def _get_diff_filename(self, res_file: str) -> str | None:
        if not self._write_diff:
            return None
        return str(Path(res_file).parent / f"diff_{Path(res_file).name}")

    def _read(self, filename: str) -> protocols.FieldData | protocols.FieldDataSequence:
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
            raise e

    def _compare_fields(
        self,
        res_fields: protocols.FieldData | protocols.FieldDataSequence,
        ref_fields: protocols.FieldData | protocols.FieldDataSequence,
        diff_filename: str | None = None,
    ) -> TestSuite:
        if isinstance(res_fields, protocols.FieldData) and isinstance(ref_fields, protocols.FieldData):
            result = self._compare_field_data(res_fields, ref_fields)
            if diff_filename is not None:
                self._write_diff_file(diff_filename, res_fields, ref_fields)
            return result
        if isinstance(res_fields, protocols.FieldDataSequence) and isinstance(ref_fields, protocols.FieldDataSequence):
            return self._compare_field_sequences(res_fields, ref_fields, diff_filename)

        def _is_unknown(fields) -> bool:
            return not isinstance(fields, protocols.FieldData) and not isinstance(fields, protocols.FieldDataSequence)

        if any(_is_unknown(f) for f in [res_fields, ref_fields]):
            raise ValueError("Unknown data type (supported are 'FieldData' / 'FieldDataSequence')")
        raise ValueError("Cannot compare sequences against field data")

    def _compare_field_sequences(
        self,
        res_sequence: protocols.FieldDataSequence,
        ref_sequence: protocols.FieldDataSequence,
        diff_basefilename: str | None = None,
    ) -> TestSuite:
        num_steps_check: TestStatus | None = None
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
            def _merged_result(r1: TestStatus | None, r2: TestStatus | None) -> TestStatus | None:
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
            if diff_basefilename is not None:
                self._write_diff_file(f"{diff_basefilename}_step_{idx}", res_step, ref_step)
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
                missing_references_is_error=(not self._opts.ignore_missing_reference_fields),
                missing_sources_is_error=(not self._opts.ignore_missing_source_fields),
            ),
            reordering_callback=lambda msg: self._logger.log(f"{msg}\n"),
        )

    def _run_field_data_comparison(
        self, result: protocols.FieldData, reference: protocols.FieldData
    ) -> FieldComparisonSuite:
        return self._invoke_comparator(
            FieldDataComparator(
                result,
                reference,
                field_inclusion_filter=self._opts.field_inclusion_filter,
                field_exclusion_filter=self._opts.field_exclusion_filter,
                missing_sources_is_error=(not self._opts.ignore_missing_source_fields),
                missing_references_is_error=(not self._opts.ignore_missing_reference_fields),
            )
        )

    def _invoke_comparator(self, comparator, **kwargs) -> FieldComparisonSuite:
        class Callback:
            def __init__(self, logger: CLILogger) -> None:
                self._logger = logger

            def __call__(self, result: FieldComparison) -> None:
                if self._logger.verbosity_level == 0:
                    return
                if (
                    result.status in [FieldComparisonStatus.passed, FieldComparisonStatus.skipped]
                    and self._logger.verbosity_level == 1
                ):
                    return
                msg = field_comparison_report(result, verbosity=max(1, self._logger.verbosity_level - 1))
                self._logger.log(f"{msg}\n" if msg else "")

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

        return TestResult(
            name=comp_result.name,
            status=self._parse_status(comp_result),
            shortlog=comp_result.report,
            stdout=_get_stdout(),
            cpu_time=comp_result.cpu_time,
        )

    def _parse_status(self, comparison: FieldComparison) -> TestStatus:
        if comparison.status == FieldComparisonStatus.failed:
            return TestStatus.error if comparison.result == FieldComparisonResult.error else TestStatus.failed
        if comparison.status == FieldComparisonStatus.passed:
            return TestStatus.passed
        if comparison.status == FieldComparisonStatus.skipped:
            return TestStatus.skipped
        raise ValueError("Could not parse field comparison status")

    def _status_string(self, status: TestStatus) -> str:
        if status == TestStatus.passed:
            return as_success("PASSED")
        if status in [TestStatus.failed, TestStatus.error]:
            return as_error("FAILED")
        return as_warning("SKIPPED")


def _make_test_suite(
    tests: list[TestResult], status: TestStatus | None, name: str | None = None, shortlog: str = ""
) -> TestSuite:
    return TestSuite(name=name, tests=tests, status=status, shortlog=shortlog)


def _suite_name(filename: str) -> str:
    path = Path(filename)
    if len(path.parts) == 1:
        return filename
    return str(Path(*path.parts[1:]))
