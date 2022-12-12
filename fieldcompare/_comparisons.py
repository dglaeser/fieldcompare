"""Classes to perform field data comparisons"""
from typing import Callable, Optional, List, Tuple, Iterator, Iterable, Any
from dataclasses import dataclass
from enum import Enum, auto

from .predicates import DefaultEquality, PredicateResult
from .protocols import Field, FieldData, Predicate

from ._matching import MatchResult, find_matches_by_name
from ._common import _measure_time


class FieldComparisonStatus(Enum):
    passed = auto()
    failed = auto()
    error = auto()
    missing_source = auto()
    missing_reference = auto()
    filtered = auto()


@dataclass
class FieldComparisonResult:
    name: str
    status: FieldComparisonStatus
    predicate: str
    report: str
    cpu_time: Optional[float] = None

    def __bool__(self) -> bool:
        return not self.is_failure

    @property
    def is_failure(self) -> bool:
        return self.status == FieldComparisonStatus.failed \
            or self.status == FieldComparisonStatus.error


class FieldComparisonSuite:
    def __init__(self,
                 domain_eq_check: PredicateResult,
                 comparisons: List[FieldComparisonResult] = []) -> None:
        self._domain_eq_check = domain_eq_check
        self._comparisons = comparisons

    def __bool__(self) -> bool:
        if not self._domain_eq_check:
            return False
        return not any(c.is_failure for c in self._comparisons)

    def __iter__(self) -> Iterator[FieldComparisonResult]:
        return iter(self._comparisons)

    @property
    def domain_equality_check(self) -> PredicateResult:
        """Return the result of the domain equality check"""
        return self._domain_eq_check

    @property
    def passed(self) -> Iterable[FieldComparisonResult]:
        """Return a range over all passed comparisons"""
        return (c for c in self._comparisons if c.status == FieldComparisonStatus.passed)

    @property
    def failed(self) -> Iterable[FieldComparisonResult]:
        """Return a range over all failed comparisons"""
        return (c for c in self._comparisons if c.is_failure)

    @property
    def skipped(self) -> Iterable[FieldComparisonResult]:
        """Return a range over all skipped comparisons"""
        return (c for c in self._comparisons if c.status in [
            FieldComparisonStatus.missing_source,
            FieldComparisonStatus.missing_reference
        ])


PredicateSelector = Callable[[Field, Field], Predicate]
FieldComparisonCallback = Callable[[FieldComparisonResult], Any]

class FieldDataComparison:
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
                 fieldcomp_callback: FieldComparisonCallback = lambda c: None) -> FieldComparisonSuite:
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
                         fieldcomp_callback: FieldComparisonCallback) -> List[FieldComparisonResult]:
        comparisons = []
        for source, reference in query.matches:
            predicate = predicate_selector(source, reference)
            try:
                comp = self._perform_comparison(source, reference, predicate)
            except Exception as e:
                comp = self._make_exception_comparison(source.name, predicate, e)
            fieldcomp_callback(comp)
            comparisons.append(comp)
        return comparisons

    def _perform_comparison(self,
                            source: Field,
                            reference: Field,
                            predicate: Predicate) -> FieldComparisonResult:
        runtime, result = _measure_time(predicate)(source.values, reference.values)
        return FieldComparisonResult(
            name=source.name,
            status=FieldComparisonStatus.passed if result else FieldComparisonStatus.failed,
            predicate=str(predicate),
            report=result.report,
            cpu_time=runtime
        )

    def _make_exception_comparison(self,
                                   name: str,
                                   predicate: Predicate,
                                   exception: Exception) -> FieldComparisonResult:
        return FieldComparisonResult(
            name=name,
            status=FieldComparisonStatus.error,
            predicate=str(predicate),
            report=f"Exception raised: {exception}",
            cpu_time=None
        )

    def _missing_source_comparisons(self, query: MatchResult) -> List[FieldComparisonResult]:
        return [
            FieldComparisonResult(
                name=field.name,
                status=FieldComparisonStatus.missing_source,
                predicate="",
                report="Missing source field"
            ) for field in query.orphans_in_reference
        ]

    def _missing_reference_comparisons(self, query: MatchResult) -> List[FieldComparisonResult]:
        return [
            FieldComparisonResult(
                name=field.name,
                status=FieldComparisonStatus.missing_reference,
                predicate="",
                report="Missing reference field"
            ) for field in query.orphans_in_source
        ]

    def _filtered_comparisons(self, filtered: List[Field]) -> List[FieldComparisonResult]:
        return [
            FieldComparisonResult(
                name=field.name,
                status=FieldComparisonStatus.filtered,
                predicate="",
                report="Filtered out by given rules"
            ) for field in filtered
        ]
