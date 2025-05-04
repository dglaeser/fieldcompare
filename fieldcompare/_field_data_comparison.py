# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Functionality for field data comparisons"""

from __future__ import annotations

import sys
from typing import Callable, Iterator, Any, TextIO
from dataclasses import dataclass
from enum import Enum, auto
from itertools import chain

from .predicates import DefaultEquality, PredicateResult
from .protocols import Field, FieldData, Predicate

from ._matching import MatchResult, find_matches_by_name
from ._common import _measure_time
from ._field import Field as FieldImpl
from ._format import remove_annotation, as_error, as_success, as_warning, highlighted, remove_color_codes


class FieldComparisonStatus(Enum):
    """Represents the status of a field comparison"""

    passed = auto()
    failed = auto()
    skipped = auto()

    def __bool__(self) -> bool:
        """This operator raises an exception to avoid accidental misuse"""
        raise NotImplementedError("FieldComparisonStatus objects are not boolean-testable")

    def __str__(self) -> str:
        """Use uppercase string representation without class name prefix"""
        return f"{self.name.upper()}"


class FieldComparisonResult(Enum):
    """The result of a field comparison"""

    equal = auto()
    unequal = auto()
    error = auto()
    missing_source = auto()
    missing_reference = auto()
    filtered = auto()

    def __str__(self) -> str:
        """Use uppercase string representation without class name prefix"""
        return f"{self.name.upper()}"


@dataclass
class FieldComparison:
    """Stores information on the results of a single field comparison."""

    name: str
    status: FieldComparisonStatus
    result: FieldComparisonResult
    predicate: str
    report: str
    cpu_time: float | None = None

    @property
    def passed(self) -> bool:
        return self.status == FieldComparisonStatus.passed

    @property
    def failed(self) -> bool:
        return self.status == FieldComparisonStatus.failed

    @property
    def skipped(self) -> bool:
        return self.status == FieldComparisonStatus.skipped


class FieldComparisonSuite:
    """
    Stores the results of a field data comparison.

    Args:
        domain_eq_check: Result of the domain equality check
        comparisons: Results of all performed field comparisons.
    """

    def __init__(self, domain_eq_check: PredicateResult, comparisons: list[FieldComparison] | None = None) -> None:
        self._domain_eq_check = domain_eq_check
        self._passed: list[FieldComparison] = []
        self._failed: list[FieldComparison] = []
        self._skipped: list[FieldComparison] = []
        if comparisons is not None:
            for c in comparisons:
                if c.passed:
                    self._passed.append(c)
                elif c.failed:
                    self._failed.append(c)
                else:
                    self._skipped.append(c)

    def __bool__(self) -> bool:
        """Return true if the suite is considered to have passed successfully."""
        if not self._domain_eq_check:
            return False
        return all(not c.failed for c in self)

    def __iter__(self) -> Iterator[FieldComparison]:
        """Return an iterator over all contained field comparison results."""
        return iter(chain(self._failed, self._passed, self._skipped))

    def __len__(self) -> int:
        """Return the number of comparisons in the suite."""
        return len(self._failed) + len(self._passed) + len(self._skipped)

    @property
    def report(self) -> str:
        """Return information about performed comparisons."""
        if not self._domain_eq_check:
            return "Domain equality check failed"

        return (
            f"{self.__len__()} field comparisons"
            f" with {self.num_passed} {FieldComparisonStatus.passed}"
            f", {self.num_failed} {FieldComparisonStatus.failed}"
            f", {self.num_skipped} {FieldComparisonStatus.skipped}"
        )

    @property
    def domain_equality_check(self) -> PredicateResult:
        """Return the result of the domain equality check."""
        return self._domain_eq_check

    @property
    def passed(self) -> list[FieldComparison]:
        """Return a range over all passed comparisons."""
        return self._passed

    @property
    def failed(self) -> list[FieldComparison]:
        """Return a range over all failed comparisons."""
        return self._failed

    @property
    def skipped(self) -> list[FieldComparison]:
        """Return a range over all skipped comparisons."""
        return self._skipped

    @property
    def num_failed(self) -> int:
        """Return the number of failed field comparisons"""
        return len(self._failed)

    @property
    def num_skipped(self) -> int:
        """Return the number of skipped field comparisons"""
        return len(self._skipped)

    @property
    def num_passed(self) -> int:
        """Return the number of passed field comparisons"""
        return len(self._passed)


def field_comparison_report(comparison: FieldComparison, use_colors: bool = True, verbosity: int = 1) -> str:
    """
    Returns a report for a given :class:`.FieldComparison`.

    Args:
        comparison: The comparison result.
        use_colors: Switch on/off colors.
        verbosity: Control the verbosity of the report.
    """
    _verbosity_level_info = 1 if not comparison.skipped else 2
    _verbosity_level_detail = 2 if not comparison.skipped else 3

    def _get_indented(message: str, indentation_level: int = 0) -> str:
        if indentation_level > 0 and message != "":
            lines = message.rstrip("\n").split("\n")
            lines = [" " + "  " * (indentation_level - 1) + f"-- {line}" for line in lines]
            message = "\n".join(lines)
        return message

    status_string = (
        as_warning(str(comparison.status))
        if comparison.skipped
        else as_error(str(comparison.status))
        if comparison.failed
        else as_success(str(comparison.status))
    )
    report = ""
    if verbosity >= _verbosity_level_info:
        report += _get_indented(
            f"Comparing the field '{highlighted(comparison.name)}': {status_string}", indentation_level=1
        )
    if verbosity >= _verbosity_level_detail or (verbosity >= _verbosity_level_info and comparison.failed):
        report += "\n"
        if comparison.result in [FieldComparisonResult.equal, FieldComparisonResult.unequal] and not comparison.skipped:
            report += _get_indented(
                f"Report: {comparison.report if comparison.report else 'n/a'}\n"
                f"Predicate: {comparison.predicate if comparison.predicate else 'n/a'}",
                indentation_level=2,
            )
        else:
            report += _get_indented(comparison.report, indentation_level=2)
    if not use_colors:
        report = remove_color_codes(report)
    return report


class DefaultFieldComparisonCallback:
    """
    Writes default status messages for each field comparison to the given stream.

    Args:
        verbosity: Integer to control the verbosity of the written output (optional). Default: 2
        use_colors: Switch on/off colors.
        stream: Stream to write to (optional). Defaults to stdout.
    """

    def __init__(self, verbosity: int = 1, use_colors: bool = True, stream: TextIO = sys.stdout) -> None:
        self._verbosity = verbosity
        self._use_colors = use_colors
        self._stream = stream

    def __call__(self, result: FieldComparison) -> None:
        """Write info on the performed field comparison into the given stream."""
        msg = field_comparison_report(comparison=result, use_colors=self._use_colors, verbosity=self._verbosity)
        self._stream.write(f"{msg}\n" if msg else "")


PredicateSelector = Callable[[Field, Field], Predicate]
FieldComparisonCallback = Callable[[FieldComparison], Any]


class FieldDataComparator:
    """
    Compares all fields in two given objects of :class:`.FieldData`.

    Args:
        source: Field data to be compared.
        reference: Reference field data to compare against.
        field_inclusion_filter: Filter to select the fields to be compared (optional).
        field_exclusion_filter: Filter to exclude fields from being compared (optional).
    """

    def __init__(  # noqa: PLR0913
        self,
        source: FieldData,
        reference: FieldData,
        field_inclusion_filter: Callable[[str], bool] = lambda _: True,
        field_exclusion_filter: Callable[[str], bool] = lambda _: False,
        missing_sources_is_error: bool = True,
        missing_references_is_error: bool = True,
    ) -> None:
        self._source = source
        self._reference = reference
        self._field_inclusion_filter = field_inclusion_filter
        self._field_exclusion_filter = field_exclusion_filter
        self._missing_sources_is_error = missing_sources_is_error
        self._missing_references_is_error = missing_references_is_error

    def __call__(
        self,
        predicate_selector: PredicateSelector | None = None,
        fieldcomp_callback: FieldComparisonCallback | None = None,
    ) -> FieldComparisonSuite:
        """
        Compare all fields in the field data objects using the given predicates.

        Args:
            predicate_selector: Selector function taking the two fields to be compared,
                                returning a predicate to be used for comparing the field values.
                                Default: :class:`.DefaultEquality`.
            fieldcomp_callback: Function that is invoked with the results of individual
                                field comparison results as soon as they are available (e.g. to
                                print intermediate output). Defaults to :class:`.DefaultFieldComparisonCallback`.
        """

        def _default_predicate_selector(*_, **__):
            return DefaultEquality()

        predicate_selector = predicate_selector or _default_predicate_selector
        fieldcomp_callback = fieldcomp_callback or DefaultFieldComparisonCallback()
        domain_eq_check = self._source.domain.equals(self._reference.domain)
        if not domain_eq_check:
            return FieldComparisonSuite(domain_eq_check=domain_eq_check)

        query = find_matches_by_name(self._source, self._reference)
        query, filtered = self._filter(query)
        comparisons = self._compare_matches(query, predicate_selector, fieldcomp_callback)

        missing_source_comparisons = self._missing_source_comparisons(query)
        for c in missing_source_comparisons:
            fieldcomp_callback(c)
        comparisons.extend(missing_source_comparisons)

        missing_reference_comparisons = self._missing_reference_comparisons(query)
        for c in missing_reference_comparisons:
            fieldcomp_callback(c)
        comparisons.extend(missing_reference_comparisons)

        filtered_comparisons = self._filtered_comparisons(filtered)
        for c in filtered_comparisons:
            fieldcomp_callback(c)
        comparisons.extend(filtered_comparisons)
        return FieldComparisonSuite(domain_eq_check=domain_eq_check, comparisons=comparisons)

    def _filter(self, query: MatchResult) -> tuple[MatchResult, list[Field]]:
        def _discard(comp: Field) -> bool:
            is_included = self._field_inclusion_filter(self._without_annotation(comp).name)
            is_excluded = self._field_exclusion_filter(self._without_annotation(comp).name)
            return not is_included or is_excluded

        filtered_result = MatchResult([], [], [])
        filtered_fields = []
        for source, target in query.matches:
            if _discard(source):
                filtered_fields.append(source)
            else:
                filtered_result.matches.append((source, target))
        for source in query.orphans_in_source:
            if _discard(source):
                filtered_fields.append(source)
            else:
                filtered_result.orphans_in_source.append(source)
        for ref in query.orphans_in_reference:
            if _discard(ref):
                filtered_fields.append(ref)
            else:
                filtered_result.orphans_in_reference.append(ref)
        return filtered_result, filtered_fields

    def _compare_matches(
        self, query: MatchResult, predicate_selector: PredicateSelector, fieldcomp_callback: FieldComparisonCallback
    ) -> list[FieldComparison]:
        comparisons = []
        # ruff: noqa: PERF203
        for source, reference in query.matches:
            predicate = predicate_selector(self._without_annotation(source), self._without_annotation(reference))
            try:
                comp = self._perform_comparison(source, reference, predicate)
            except Exception as e:
                comp = self._make_exception_comparison(source.name, predicate, e)
            fieldcomp_callback(comp)
            comparisons.append(comp)
        return comparisons

    def _without_annotation(self, field: Field) -> Field:
        return FieldImpl(name=remove_annotation(field.name), values=field.values)

    def _perform_comparison(self, source: Field, reference: Field, predicate: Predicate) -> FieldComparison:
        runtime, result = _measure_time(predicate)(source.values, reference.values)
        return FieldComparison(
            name=source.name,
            status=FieldComparisonStatus.passed if result else FieldComparisonStatus.failed,
            result=FieldComparisonResult.equal if result else FieldComparisonResult.unequal,
            predicate=str(predicate),
            report=result.report,
            cpu_time=runtime,
        )

    def _make_exception_comparison(self, name: str, predicate: Predicate, exception: Exception) -> FieldComparison:
        return FieldComparison(
            name=name,
            status=FieldComparisonStatus.failed,
            result=FieldComparisonResult.error,
            predicate=str(predicate),
            report=f"Exception raised: {exception}",
            cpu_time=None,
        )

    def _missing_source_comparisons(self, query: MatchResult) -> list[FieldComparison]:
        return [
            FieldComparison(
                name=field.name,
                status=FieldComparisonStatus.failed
                if self._missing_sources_is_error
                else FieldComparisonStatus.skipped,
                result=FieldComparisonResult.missing_source,
                predicate="",
                report="Missing source field",
            )
            for field in query.orphans_in_reference
        ]

    def _missing_reference_comparisons(self, query: MatchResult) -> list[FieldComparison]:
        return [
            FieldComparison(
                name=field.name,
                status=FieldComparisonStatus.failed
                if self._missing_references_is_error
                else FieldComparisonStatus.skipped,
                result=FieldComparisonResult.missing_reference,
                predicate="",
                report="Missing reference field",
            )
            for field in query.orphans_in_source
        ]

    def _filtered_comparisons(self, filtered: list[Field]) -> list[FieldComparison]:
        return [
            FieldComparison(
                name=field.name,
                status=FieldComparisonStatus.skipped,
                result=FieldComparisonResult.filtered,
                predicate="",
                report="Filtered out by given rules",
            )
            for field in filtered
        ]
