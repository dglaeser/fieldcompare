"""Command-line interface for comparing a pair of files"""

from argparse import ArgumentParser
from textwrap import indent
from typing import List, Iterable
from dataclasses import dataclass

from ..colors import make_colored, TextStyle
from ..matching import find_matching_field_names
from ..predicates import DefaultEquality
from ..logging import Logger, StandardOutputLogger
from ..field import FieldInterface

from ._common import _read_fields_from_file, _bool_to_exit_code
from ._common import _style_as_error, _style_as_warning, _make_list_string, _get_status_string
from ._common import _parse_field_tolerances, FieldToleranceMap


@dataclass
class FileComparisonOptions:
    ignore_missing_result_fields: bool = False
    ignore_missing_reference_fields: bool = False
    relative_tolerances: FieldToleranceMap = FieldToleranceMap()
    absolute_tolerances: FieldToleranceMap = FieldToleranceMap()


@dataclass
class FieldComparison:
    name: str
    result_field: FieldInterface
    reference_field: FieldInterface


class FieldComparisonRange:
    def __init__(self,
                 res_fields: Iterable[FieldInterface],
                 ref_fields: Iterable[FieldInterface],
                 field_names: Iterable[str]) -> None:
        self._res_fields_dict: dict = {field.name: field.values for field in res_fields}
        self._ref_fields_dict: dict = {field.name: field.values for field in ref_fields}
        self._field_names = field_names
        self._field_name_iterator = iter(self._field_names)

    def __iter__(self):
        self._field_name_iterator = iter(self._field_names)
        return self

    def __next__(self) -> FieldComparison:
        name = next(self._field_name_iterator)
        res_field = self._res_fields_dict[name]
        ref_field = self._ref_fields_dict[name]
        return FieldComparison(name, res_field, ref_field)

class FileComparison:
    def __init__(self,
                 res_file: str,
                 ref_file: str,
                 options: FileComparisonOptions = FileComparisonOptions(),
                 logger: Logger = StandardOutputLogger()):
        self._options = options
        self._logger = logger

        res_fields = self._read_file(res_file)
        ref_fields = self._read_file(ref_file)

        self._match_result = find_matching_field_names(res_fields, ref_fields)

        self._comparisons = FieldComparisonRange(res_fields, ref_fields, self._match_result.matches)

    def _read_file(self, file_name: str) -> Iterable[FieldInterface]:
        try:
            return _read_fields_from_file(file_name, self._logger)
        except IOError as e:
            raise Exception(_read_error_message(file_name, str(e)))

    def run_file_compare(self) -> bool:
        try:
            passed = self._do_field_comparisons()
        except Exception as e:
            self._logger.log(f"Error upon field comparisons. Exception:\n{e}\n", verbosity_level=1)
            return False

        missing_results = self._match_result.orphan_references
        missing_references = self._match_result.orphan_results
        _log_missing_results(missing_results, self._options.ignore_missing_result_fields, self._logger)
        _log_missing_references(missing_references, self._options.ignore_missing_reference_fields, self._logger)
        passed = False if missing_results and not self._options.ignore_missing_result_fields else passed
        passed = False if missing_references and not self._options.ignore_missing_reference_fields else passed

        self._logger.log("File comparison {}\n".format(_get_status_string(passed)))
        return passed

    def _do_field_comparisons(self) -> bool:
        passed = True
        rel_tol = self._options.relative_tolerances
        abs_tol = self._options.absolute_tolerances
        for comp in self._comparisons:
            name = comp.name
            predicate = DefaultEquality(rel_tol=rel_tol.get(name), abs_tol=abs_tol.get(name))
            result = predicate(comp.result_field, comp.reference_field)
            msg = _get_comparison_message_string(name, bool(result))
            report = _get_predicate_report_string(result.predicate_info, result.report)
            passed = False if not result else passed
            self._logger.log(msg, verbosity_level=1)
            self._logger.log(indent(report, " -- "), verbosity_level=2)
        return passed

def _add_field_options_args(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--ignore-missing-result-fields",
        required=False,
        action="store_true",
        help="Use this flag to treat missing result fields as warnings only"
    )
    parser.add_argument(
        "--ignore-missing-reference-fields",
        required=False,
        action="store_true",
        help="Use this flag to treat missing reference fields as warnings only"
    )


def _add_tolerance_options_args(parser: ArgumentParser) -> None:
    parser.add_argument(
        "-rtol", "--relative-tolerance",
        required=False,
        nargs="*",
        help="Specify the relative tolerance to be used. "
             "Use e.g. '-rtol 1e-3:pressure' to set the tolerance for a field named 'pressure'"
    )
    parser.add_argument(
        "-atol", "--absolute-tolerance",
        required=False,
        nargs="*",
        help="Specify the absolute tolerance to be used. "
             "Use e.g. '-atol 1e-3:pressure' to set the tolerance for a field named 'pressure'"
    )


def _add_arguments(parser: ArgumentParser):
    parser.add_argument(
        "file",
        type=str,
        help="The file which is to be compared against a reference file"
    )
    parser.add_argument(
        "-r", "--reference",
        required=True,
        type=str,
        help="The reference file against which to compare"
    )
    parser.add_argument(
        "--verbosity",
        required=False,
        default=2,
        type=int,
        help="Set the verbosity level"
    )
    _add_field_options_args(parser)
    _add_tolerance_options_args(parser)


def _run(args: dict, logger: Logger) -> int:
    if not logger.verbosity_level:
        logger.verbosity_level = args["verbosity"]

    opts = FileComparisonOptions(
        ignore_missing_result_fields=args["ignore_missing_result_fields"],
        ignore_missing_reference_fields=args["ignore_missing_reference_fields"],
        relative_tolerances=_parse_field_tolerances(args.get("relative_tolerance")),
        absolute_tolerances=_parse_field_tolerances(args.get("absolute_tolerance"))
    )

    try:
        comparison = FileComparison(args["file"], args["reference"], opts, logger)
        passed = comparison.run_file_compare()
    except Exception as e:
        logger.log(str(e), verbosity_level=1)
        return False

    return _bool_to_exit_code(passed)


def _log_missing_results(missing_results: List[str], ignore_missing_res: bool, logger: Logger) -> None:
    if missing_results:
        should_fail = not ignore_missing_res
        logger.log(
            "{}\n".format(_missing_res_or_ref_message("result", should_fail)),
            verbosity_level=1
        )
        logger.log(
            "{}\n".format(_make_list_string(missing_results)),
            verbosity_level=1
        )


def _log_missing_references(missing_references: List[str], ignore_missing_ref: bool, logger: Logger) -> None:
    if missing_references:
        should_fail = not ignore_missing_ref
        logger.log(
            "{}\n".format(_missing_res_or_ref_message("reference", should_fail)),
            verbosity_level=1
        )
        logger.log(
            "{}\n".format(_make_list_string(missing_references)),
            verbosity_level=1
        )


def _read_error_message(filename: str, except_str: str) -> str:
    if not except_str.endswith("\n"):
        except_str = f"{except_str}\n"
    return _style_as_error("Error") + f" reading '{filename}':\n" + indent(except_str, " "*4)


def _missing_res_or_ref_message(res_or_ref: str, is_error: bool) -> str:
    result = f"missing {res_or_ref} fields"
    if is_error:
        result = _style_as_error(f"Error: {result}")
    else:
        result = "Ignored the following " + _style_as_warning(result)
    return result


def _get_comparison_message_string(field_name: str, status: bool) -> str:
    return "Comparison of the fields '{}' and '{}': {}\n".format(
        make_colored(field_name, style=TextStyle.bright),
        make_colored(field_name, style=TextStyle.bright),
        _get_status_string(status)
    )


def _get_predicate_report_string(pred_info: str, pred_log: str) -> str:
    return f"Predicate: {pred_info}\nReport: {pred_log}\n"
