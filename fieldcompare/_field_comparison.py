"""Class to perform a comparison of two field containers"""

from textwrap import indent
from typing import Iterable, List, Callable
from dataclasses import dataclass

from ._array import Array
from ._colors import make_colored, TextStyle
from ._matching import find_matching_names
from ._predicates import DefaultEquality
from ._field import FieldContainerInterface
from ._logging import LoggerInterface, StandardOutputLogger

from ._common import _default_base_tolerance
from ._format import (
    as_error,
    as_warning,
    get_status_string,
    make_list_string
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
    """Class to perform a comparison of two files"""
    def __init__(self,
                 options: FieldComparisonOptions = FieldComparisonOptions(),
                 logger: LoggerInterface = StandardOutputLogger()):
        self._options = options
        self._logger = logger

    def __call__(self,
                 res_fields: FieldContainerInterface,
                 ref_fields: FieldContainerInterface) -> bool:
        """Check two field containers for equality of the contained fields"""
        try:
            self._prepare_comparison_range(res_fields, ref_fields)
        except Exception as e:
            self._logger.log(f"Error preparing field comparison. Exception:\n{e}\n", verbosity_level=1)
            return False

        try:
            passed = self._do_field_comparisons()
        except Exception as e:
            self._logger.log(f"Error upon field comparisons. Exception:\n{e}\n", verbosity_level=1)
            return False
        missing_results = self._missing_result_fields
        missing_references = self._missing_reference_fields
        _log_missing_results(missing_results, self._options.ignore_missing_result_fields, self._logger)
        _log_missing_references(missing_references, self._options.ignore_missing_reference_fields, self._logger)
        passed = False if missing_results and not self._options.ignore_missing_result_fields else passed
        passed = False if missing_references and not self._options.ignore_missing_reference_fields else passed
        return passed

    def _prepare_comparison_range(self,
                                  res_fields: FieldContainerInterface,
                                  ref_fields: FieldContainerInterface) -> None:
        self._find_fields_to_compare(res_fields.field_names, ref_fields.field_names)
        self._comparisons = _FieldComparisonRange(res_fields, ref_fields, self._fields_to_compare)

    def _find_fields_to_compare(self,
                                res_fields: Iterable[str],
                                ref_fields: Iterable[str]) -> None:
        match_result = find_matching_names(res_fields, ref_fields)

        self._fields_to_compare = self._apply_field_inclusion_filter(match_result.matches)
        self._missing_result_fields = self._apply_field_inclusion_filter(match_result.orphan_references)
        self._missing_reference_fields = self._apply_field_inclusion_filter(match_result.orphan_results)

        self._fields_to_compare = self._apply_field_exclusion_filter(self._fields_to_compare)
        self._missing_result_fields = self._apply_field_exclusion_filter(self._missing_result_fields)
        self._missing_reference_fields = self._apply_field_exclusion_filter(self._missing_reference_fields)

    def _apply_field_inclusion_filter(self, fields: List[str]) -> List[str]:
        if self._options.field_inclusion_filter:
            fields = self._options.field_inclusion_filter(fields)
        return fields

    def _apply_field_exclusion_filter(self, fields: List[str]) -> List[str]:
        if self._options.field_exclusion_filter:
            to_exclude = set(self._options.field_exclusion_filter(fields))
            fields = list(set(fields).difference(to_exclude))
        return fields

    def _do_field_comparisons(self) -> bool:
        passed = True
        rel_tol = self._options.relative_tolerances
        abs_tol = self._options.absolute_tolerances

        num_comps = 0
        for comp in self._comparisons:
            name = comp.field_name
            predicate = DefaultEquality(rel_tol=rel_tol(name), abs_tol=abs_tol(name))
            result = predicate(comp.result_values, comp.reference_values)
            msg = _get_comparison_message_string(name, bool(result))
            report = _get_predicate_report_string(result.predicate_info, result.report)
            passed = False if not result else passed
            self._logger.log(msg, verbosity_level=1)
            self._logger.log(indent(report, " -- "), verbosity_level=2)
            num_comps += 1

        if num_comps == 0:
            self._logger.log("No fields found to compare\n", verbosity_level=1)

        return passed


@dataclass
class _Comparison:
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

    def __next__(self) -> _Comparison:
        name = next(self._field_name_iterator)
        res_field = self._res_fields.get(name).values
        ref_field = self._ref_fields.get(name).values
        return _Comparison(name, res_field, ref_field)


def _log_missing_results(missing_results: List[str],
                         ignore_missing_res: bool,
                         logger: LoggerInterface) -> None:
    if missing_results:
        should_fail = not ignore_missing_res
        logger.log(
            "{}\n".format(_missing_res_or_ref_message("result", should_fail)),
            verbosity_level=1
        )
        logger.log(
            "{}\n".format(make_list_string(missing_results)),
            verbosity_level=1
        )


def _log_missing_references(missing_references: List[str],
                            ignore_missing_ref: bool,
                            logger: LoggerInterface) -> None:
    if missing_references:
        should_fail = not ignore_missing_ref
        logger.log(
            "{}\n".format(_missing_res_or_ref_message("reference", should_fail)),
            verbosity_level=1
        )
        logger.log(
            "{}\n".format(make_list_string(missing_references)),
            verbosity_level=1
        )


def _missing_res_or_ref_message(res_or_ref: str, is_error: bool) -> str:
    result = f"missing {res_or_ref} fields"
    if is_error:
        result = as_error(f"Error: {result}")
    else:
        result = "Ignored the following " + as_warning(result)
    return result


def _get_comparison_message_string(field_name: str, status: bool) -> str:
    return "Comparison of the field '{}': {}\n".format(
        make_colored(field_name, style=TextStyle.bright),
        get_status_string(status)
    )


def _get_predicate_report_string(pred_info: str, pred_log: str) -> str:
    return f"Predicate: {pred_info}\nReport: {pred_log}\n"
