"""Classes to perform field data comparisons"""
from typing import Callable, Optional, List, Iterator, Iterable, Any
from dataclasses import dataclass
from enum import Enum, auto

from .predicates import DefaultEquality
from .protocols import Field, FieldData, Predicate

from ._matching import MatchResult, find_matches_by_name
from ._common import _measure_time


class FieldComparisonStatus(Enum):
    passed = auto()
    failed = auto()
    error = auto()
    missing_source = auto()
    missing_reference = auto()


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
                 comparisons: List[FieldComparisonResult] = [],
                 err_msg: str = "") -> None:
        self._comparisons = comparisons
        self._err_msg = err_msg

    def __bool__(self) -> bool:
        return False if self._err_msg else not any(c.is_failure for c in self._comparisons)

    def __iter__(self) -> Iterator[FieldComparisonResult]:
        return iter(self._comparisons)

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
    def __init__(self, source: FieldData, reference: FieldData) -> None:
        self._source = source
        self._reference = reference

    def __call__(self,
                 predicate_selector: PredicateSelector = lambda _, __: DefaultEquality(),
                 fieldcomp_callback: FieldComparisonCallback = lambda c: None) -> FieldComparisonSuite:
        domain_eq_check = self._source.domain.equals(self._reference.domain)
        if not domain_eq_check:
            return FieldComparisonSuite(err_msg=domain_eq_check.report)

        query = find_matches_by_name(self._source, self._reference)
        comparisons = self._compare_matches(query, predicate_selector, fieldcomp_callback)
        comparisons.extend(self._missing_source_comparisons(query))
        comparisons.extend(self._missing_reference_comparisons(query))
        return FieldComparisonSuite(comparisons=comparisons)

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
