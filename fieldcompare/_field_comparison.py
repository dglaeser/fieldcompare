"""Class to perform a comparison of two field containers"""

from textwrap import indent
from typing import Iterable, List, Callable
from dataclasses import dataclass

from .predicates import DefaultEquality

from ._array import Array
from ._matching import find_matches
from ._field import FieldContainerInterface
from ._logging import LoggerInterface, StandardOutputLogger

from ._comparison import Comparison, Status
from ._comparison import ComparisonSuite

from ._common import _default_base_tolerance, _measure_time
from ._format import (
    as_error,
    as_warning,
    highlighted,
    get_status_string,
    make_indented_list_string
)


def _default_tolerance_map(field_name: str) -> float:
    return _default_base_tolerance()


def _all_inclusion_filter(names: List[str]) -> List[str]:
    return names


def _null_exclusion_filter(names: List[str]) -> List[str]:
    return []


@dataclass
class FieldComparisonOptions:
    ignore_missing_result_fields: bool = False
    ignore_missing_reference_fields: bool = False
    relative_tolerances: Callable[[str], float] = _default_tolerance_map
    absolute_tolerances: Callable[[str], float] = _default_tolerance_map
    field_inclusion_filter: Callable[[List[str]], List[str]] = _all_inclusion_filter
    field_exclusion_filter: Callable[[List[str]], List[str]] = _null_exclusion_filter


class FieldComparison:
    """Class to perform a comparison of two field containers"""
    def __init__(self,
                 options: FieldComparisonOptions = FieldComparisonOptions(),
                 logger: LoggerInterface = StandardOutputLogger()):
        self._options = options
        self._logger = logger

    def __call__(self,
                 res_fields: FieldContainerInterface,
                 ref_fields: FieldContainerInterface) -> ComparisonSuite:
        """Check two field containers for equality of the contained fields"""
        try:
            self._prepare_comparison_range(res_fields, ref_fields)
        except Exception as e:
            msg = f"Error preparing field comparison. Exception:\n{e}\n"
            self._logger.log(msg, verbosity_level=1)
            return ComparisonSuite(Status.error, msg)

        try:
            comparisons = self._do_field_comparisons()
        except Exception as e:
            msg = f"Error upon field comparisons. Exception:\n{e}\n"
            self._logger.log(msg, verbosity_level=1)
            return ComparisonSuite(Status.error, msg)

        self._handle_uncompared_fields(comparisons)
        return comparisons

    def _prepare_comparison_range(self,
                                  res_fields: FieldContainerInterface,
                                  ref_fields: FieldContainerInterface) -> None:
        self._find_fields_to_compare(res_fields.field_names, ref_fields.field_names)
        self._comparisons = _FieldComparisonRange(res_fields, ref_fields, self._fields_to_compare)

    def _find_fields_to_compare(self,
                                res_fields: Iterable[str],
                                ref_fields: Iterable[str]) -> None:
        match_result = find_matches(list(res_fields), list(ref_fields))
        self._filtered_fields: set = set()

        self._fields_to_compare = self._apply_field_inclusion_filter(list(n for n, _ in match_result.matches))
        self._missing_result_fields = self._apply_field_inclusion_filter(match_result.orphans_in_reference)
        self._missing_reference_fields = self._apply_field_inclusion_filter(match_result.orphans_in_source)

        self._fields_to_compare = self._apply_field_exclusion_filter(self._fields_to_compare)
        self._missing_result_fields = self._apply_field_exclusion_filter(self._missing_result_fields)
        self._missing_reference_fields = self._apply_field_exclusion_filter(self._missing_reference_fields)

    def _apply_field_inclusion_filter(self, fields: List[str]) -> List[str]:
        include = self._options.field_inclusion_filter(fields)
        self._filtered_fields = self._filtered_fields.union(set(fields).difference(set(include)))
        return include

    def _apply_field_exclusion_filter(self, fields: List[str]) -> List[str]:
        to_exclude = set(self._options.field_exclusion_filter(fields))
        fields = list(set(fields).difference(to_exclude))
        self._filtered_fields = self._filtered_fields.union(to_exclude)
        return fields

    def _do_field_comparisons(self) -> ComparisonSuite:
        comparisons = ComparisonSuite()
        for comp in self._comparisons:
            cpu_time, comparison = _measure_time(lambda c: self._do_field_comparison(c))(comp)
            comparison.cpu_time = cpu_time
            comparisons.insert(comparison)
        return comparisons

    def _do_field_comparison(self, comp) -> Comparison:
        name = comp.field_name
        predicate = DefaultEquality(
            rel_tol=self._options.relative_tolerances(name),
            abs_tol=self._options.absolute_tolerances(name)
        )

        result = predicate(comp.result_values, comp.reference_values)
        status = Status.passed if bool(result) else Status.failed

        msg = _get_comparison_message_string(name, bool(result))
        report = indent(_get_predicate_report_string(str(predicate), result.report), " -- ")
        self._logger.log(msg, verbosity_level=1)
        self._logger.log(report, verbosity_level=2)
        return Comparison(name, status, f"{msg}{report}")

    def _handle_uncompared_fields(self, comparisons):
        _log_unhandled_fields(
            _missing_res_or_ref_message("result", not self._options.ignore_missing_result_fields),
            self._missing_result_fields,
            self._logger,
            verbosity_level=1
        )
        _log_unhandled_fields(
            _missing_res_or_ref_message("reference", not self._options.ignore_missing_reference_fields),
            self._missing_reference_fields,
            self._logger,
            verbosity_level=1
        )
        _log_unhandled_fields(
            as_warning("Fields that were filtered out by the given wildcard patterns:"),
            list(self._filtered_fields),
            self._logger,
            verbosity_level=2
        )

        _insert_missing_field_comparisons(
            comparisons,
            self._missing_result_fields,
            self._options.ignore_missing_result_fields,
            "missing result field"
        )
        _insert_missing_field_comparisons(
            comparisons,
            self._missing_reference_fields,
            self._options.ignore_missing_reference_fields,
            "missing reference field"
        )
        _insert_missing_field_comparisons(
            comparisons,
            list(self._filtered_fields),
            treat_as_skipped=True,
            reason="Filtered out by given wildcard patterns"
        )


@dataclass
class _FieldComparison:
    field_name: str
    result_values: Array
    reference_values: Array


class _FieldComparisonRange:
    def __init__(self,
                 res_fields: FieldContainerInterface,
                 ref_fields: FieldContainerInterface,
                 field_names: List[str]) -> None:
        self._res_fields = res_fields
        self._ref_fields = ref_fields
        self._field_names = field_names
        self._field_name_iterator = iter(self._field_names)

    def __iter__(self):
        self._field_name_iterator = iter(self._field_names)
        return self

    def __next__(self) -> _FieldComparison:
        name = next(self._field_name_iterator)
        res_field = self._res_fields.get(name).values
        ref_field = self._ref_fields.get(name).values
        return _FieldComparison(name, res_field, ref_field)


def _log_unhandled_fields(header: str,
                          names: List[str],
                          logger: LoggerInterface,
                          verbosity_level: int) -> None:
    if names:
        logger.log(f"{header}\n", verbosity_level=verbosity_level)
        logger.log(f"{make_indented_list_string(names)}\n", verbosity_level=verbosity_level)


def _insert_missing_field_comparisons(result: ComparisonSuite,
                                      missing_field_names: List[str],
                                      treat_as_skipped: bool,
                                      reason: str):
    for name in missing_field_names:
        result.insert(Comparison(
            name=name,
            status=(Status.skipped if treat_as_skipped else Status.failed),
            stdout=reason
        ))


def _missing_res_or_ref_message(res_or_ref: str, is_error: bool) -> str:
    result = f"missing {res_or_ref} fields"
    if is_error:
        result = as_error("Error") + f": {result}"
    else:
        result = as_warning("Ignored") + f" {result}"
    return result


def _get_comparison_message_string(field_name: str, status: bool) -> str:
    return f"Comparison of the field '{highlighted(field_name)}': {get_status_string(status)}\n"


def _get_predicate_report_string(pred_info: str, pred_log: str) -> str:
    return f"Predicate: {pred_info}\nReport: {pred_log}\n"
