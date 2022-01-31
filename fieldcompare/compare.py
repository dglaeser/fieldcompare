"""Functions for comparing lists of fields."""

from typing import Optional, Callable, Iterable, List, Dict, Tuple
from dataclasses import dataclass

from .field import Field
from .matching import find_matching_field_names
from .predicates import Predicate, DefaultEquality


@dataclass
class ComparisonLog:
    result_field_name: str
    reference_field_name: str
    predicate: str
    predicate_log: str
    passed: bool


class ComparisonResult:
    def __init__(self, logs: List[ComparisonLog]):
        self._comparison_logs = logs
        self._iter = iter(self._comparison_logs)

    def __bool__(self):
        return self.num_passed_comparisons == self.num_comparisons

    def __iter__(self):
        self._iter = iter(self._comparison_logs)
        return self

    def __next__(self):
        return next(self._iter)

    @property
    def comparison_logs(self) -> List[ComparisonLog]:
        return self._comparison_logs

    @property
    def num_comparisons(self) -> int:
        return len(self._comparison_logs)

    @property
    def passed_comparison_logs(self) -> Iterable[ComparisonLog]:
        return filter(lambda log: log.passed, self._comparison_logs)

    @property
    def num_passed_comparisons(self) -> int:
        return len(list(self.passed_comparison_logs))

    @property
    def failed_comparison_logs(self) -> Iterable[ComparisonLog]:
        return filter(lambda log: not log.passed, self._comparison_logs)

    @property
    def num_failed_comparisons(self) -> int:
        return len(list(self.failed_comparison_logs))


PredicateMap = Callable[[str, str], Predicate]
FieldComparisonMap = Dict[str, List[str]]
LogCallBack = Callable[[ComparisonLog], None]

def _null_logger(log: ComparisonLog) -> None:
    pass

def compare_fields(result_fields: Iterable[Field],
                   reference_fields: Iterable[Field],
                   field_comparison_map: FieldComparisonMap,
                   predicate_map: PredicateMap,
                   log_call_back: LogCallBack = _null_logger) -> ComparisonResult:
    logs: list = []
    for result_field in result_fields:
        if result_field.name not in field_comparison_map:
            continue
        for reference_field in reference_fields:
            if reference_field.name in field_comparison_map[result_field.name]:
                predicate = predicate_map(result_field.name, reference_field.name)
                result = predicate(result_field.values, reference_field.values)
                log = ComparisonLog(
                    result_field_name=result_field.name,
                    reference_field_name=reference_field.name,
                    predicate=str(result.predicate_info),
                    predicate_log=result.report,
                    passed=bool(result)
                )

                logs.append(log)
                log_call_back(log)
    return ComparisonResult(logs)

def compare_fields_equal(result_fields: Iterable[Field],
                         reference_fields: Iterable[Field],
                         field_comparison_map: FieldComparisonMap,
                         log_call_back: LogCallBack = _null_logger) -> ComparisonResult:
    return compare_fields(
        result_fields,
        reference_fields,
        field_comparison_map,
        lambda n1, n2: DefaultEquality(),
        log_call_back
    )


@dataclass
class SkipLog:
    result_field_name: Optional[str]
    reference_field_name: Optional[str]
    reason: str

def compare_matching_fields(
        result_fields: Iterable[Field],
        reference_fields: Iterable[Field],
        predicate_map: PredicateMap,
        log_call_back: LogCallBack = _null_logger) -> Tuple[ComparisonResult, List[SkipLog]]:
    search_result = find_matching_field_names(result_fields, reference_fields)
    comparison_logs = compare_fields(
        result_fields,
        reference_fields,
        {m: [m] for m in search_result.matches},
        predicate_map,
        log_call_back
    )

    skipped_logs: list = []
    for skipped_result_field in search_result.orphan_results:
        skipped_logs.append(SkipLog(
            result_field_name=skipped_result_field,
            reference_field_name=None,
            reason="Field not present in the references"
        ))
    for skipped_reference_field in search_result.orphan_references:
        skipped_logs.append(SkipLog(
            result_field_name=None,
            reference_field_name=skipped_reference_field,
            reason="Reference field not present in the result fields"
        ))

    return comparison_logs, skipped_logs

def compare_matching_fields_equal(
        result_fields: Iterable[Field],
        reference_fields: Iterable[Field],
        log_call_back: LogCallBack = _null_logger) -> Tuple[ComparisonResult, List[SkipLog]]:
    return compare_matching_fields(
        result_fields,
        reference_fields,
        lambda n1, n2: DefaultEquality(),
        log_call_back
    )
