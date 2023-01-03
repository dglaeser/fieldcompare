"""Functionality for field data comparisons"""

from typing import Callable, Optional, List, Tuple, Iterator, Any
from dataclasses import dataclass
from enum import Enum, auto
from itertools import chain

from .predicates import DefaultEquality, PredicateResult
from .protocols import Field, FieldData, Predicate

from ._matching import MatchResult, find_matches_by_name
from ._common import _measure_time
from ._format import remove_annotation
from ._field import Field as FieldImpl


class Status(Enum):
    passed = auto()
    failed = auto()

    def __bool__(self) -> bool:
        """Return true if the status is considered successful."""
        return self not in (Status.failed,)

    def __str__(self):
        """Use uppercase string representation without class name prefix"""
        return f"{self.name.upper()}"


class FieldComparisonStatus(Enum):
    """Represents the status of a single field comparison."""
    passed = auto()
    failed = auto()
    error = auto()
    missing_source = auto()
    missing_reference = auto()
    filtered = auto()

    def __bool__(self) -> bool:
        """Return true if the status is considered successful."""
        return self not in [FieldComparisonStatus.failed, FieldComparisonStatus.error]

    def __str__(self):
        """Use uppercase string representation without class name prefix"""
        return f"{self.name.upper()}"


@dataclass
class FieldComparison:
    """Stores information on the results of a single field comparison."""
    name: str
    status: FieldComparisonStatus
    predicate: str
    report: str
    cpu_time: Optional[float] = None

    def __bool__(self) -> bool:
        """Return true if the field comparison is considered successful."""
        return not self.is_failure

    @property
    def is_failure(self) -> bool:
        """Return true if the field comparison is considered unsuccessful."""
        return not self.status


class FieldComparisonSuite:
    """
    Stores the results of a field data comparison.

    Args:
        domain_eq_check: Result of the domain equality check
        comparisons: Results of all performed field comparisons.
    """
    def __init__(self,
                 domain_eq_check: PredicateResult,
                 comparisons: List[FieldComparison] = []) -> None:
        self._domain_eq_check = domain_eq_check
        self._passed: List[FieldComparison] = []
        self._failed: List[FieldComparison] = []
        self._skipped: List[FieldComparison] = []
        for c in comparisons:
            if c.status == FieldComparisonStatus.passed:
                self._passed.append(c)
            elif not c:
                self._failed.append(c)
            else:
                self._skipped.append(c)

    def __bool__(self) -> bool:
        """Return true if the suite is considered to have passed successfully."""
        if not self._domain_eq_check:
            return False
        return not len(self._failed)

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
            f", {self.num_skipped} SKIPPED"
        )

    @property
    def status(self) -> Status:
        """Return combined status performed comparisons."""
        if not self._domain_eq_check:
            return Status.failed
        if self.num_failed > 0:
            return Status.failed
        return Status.passed

    @property
    def domain_equality_check(self) -> PredicateResult:
        """Return the result of the domain equality check."""
        return self._domain_eq_check

    @property
    def passed(self) -> List[FieldComparison]:
        """Return a range over all passed comparisons."""
        return self._passed

    @property
    def failed(self) -> List[FieldComparison]:
        """Return a range over all failed comparisons."""
        return self._failed

    @property
    def skipped(self) -> List[FieldComparison]:
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
    def __init__(self,
                 source: FieldData,
                 reference: FieldData,
                 field_inclusion_filter: Callable[[str], bool] = lambda _: True,
                 field_exclusion_filter: Callable[[str], bool] = lambda _: False) -> None:
        self._source = source
        self._reference = reference
        self._field_inclusion_filter = field_inclusion_filter
        self._field_exclusion_filter = field_exclusion_filter

    def __call__(self,
                 predicate_selector: PredicateSelector = lambda _, __: DefaultEquality(),
                 fieldcomp_callback: FieldComparisonCallback = lambda _: None) -> FieldComparisonSuite:
        """
        Compare all fields in the field data objects using the given predicates.

        Args:
            predicate_selector: Selector function taking the two fields to be compared,
                                returning a predicate to be used for comparing the field values.
                                Default: :class:`.DefaultEquality`.
            fieldcomp_callback: Function that is invoked with the results of individual
                                field comparison results as soon as they are available (e.g. to
                                print intermediate output). Default: no-op lambda.
        """
        domain_eq_check = self._source.domain.equals(self._reference.domain)
        if not domain_eq_check:
            return FieldComparisonSuite(domain_eq_check=domain_eq_check)

        query = find_matches_by_name(self._source, self._reference)
        query, filtered = self._filter_matches(query)
        comparisons = self._compare_matches(query, predicate_selector, fieldcomp_callback)
        comparisons.extend(self._missing_source_comparisons(query))
        comparisons.extend(self._missing_reference_comparisons(query))
        comparisons.extend(self._filtered_comparisons(filtered))
        return FieldComparisonSuite(domain_eq_check=domain_eq_check, comparisons=comparisons)

    def _filter_matches(self, query: MatchResult) -> Tuple[MatchResult, List[Field]]:
        filtered = []
        matching_pairs = []
        for i, (source, target) in enumerate(query.matches):
            if not self._field_inclusion_filter(source.name) \
                    or self._field_exclusion_filter(source.name):
                filtered.append(source)
            else:
                matching_pairs.append((source, target))
        query.matches = matching_pairs
        return query, filtered

    def _compare_matches(self,
                         query: MatchResult,
                         predicate_selector: PredicateSelector,
                         fieldcomp_callback: FieldComparisonCallback) -> List[FieldComparison]:
        comparisons = []
        for source, reference in query.matches:
            predicate = predicate_selector(
                self._without_annotation(source),
                self._without_annotation(reference)
            )
            try:
                comp = self._perform_comparison(source, reference, predicate)
            except Exception as e:
                comp = self._make_exception_comparison(source.name, predicate, e)
            fieldcomp_callback(comp)
            comparisons.append(comp)
        return comparisons

    def _without_annotation(self, field: Field) -> Field:
        return FieldImpl(
            name=remove_annotation(field.name),
            values=field.values
        )

    def _perform_comparison(self,
                            source: Field,
                            reference: Field,
                            predicate: Predicate) -> FieldComparison:
        runtime, result = _measure_time(predicate)(source.values, reference.values)
        return FieldComparison(
            name=source.name,
            status=FieldComparisonStatus.passed if result else FieldComparisonStatus.failed,
            predicate=str(predicate),
            report=result.report,
            cpu_time=runtime
        )

    def _make_exception_comparison(self,
                                   name: str,
                                   predicate: Predicate,
                                   exception: Exception) -> FieldComparison:
        return FieldComparison(
            name=name,
            status=FieldComparisonStatus.error,
            predicate=str(predicate),
            report=f"Exception raised: {exception}",
            cpu_time=None
        )

    def _missing_source_comparisons(self, query: MatchResult) -> List[FieldComparison]:
        return [
            FieldComparison(
                name=field.name,
                status=FieldComparisonStatus.missing_source,
                predicate="",
                report="Missing source field"
            ) for field in query.orphans_in_reference
        ]

    def _missing_reference_comparisons(self, query: MatchResult) -> List[FieldComparison]:
        return [
            FieldComparison(
                name=field.name,
                status=FieldComparisonStatus.missing_reference,
                predicate="",
                report="Missing reference field"
            ) for field in query.orphans_in_source
        ]

    def _filtered_comparisons(self, filtered: List[Field]) -> List[FieldComparison]:
        return [
            FieldComparison(
                name=field.name,
                status=FieldComparisonStatus.filtered,
                predicate="",
                report="Filtered out by given rules"
            ) for field in filtered
        ]
