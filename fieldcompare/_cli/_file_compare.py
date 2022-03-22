"""Command-line interface for comparing a pair of files"""

from argparse import ArgumentParser
from textwrap import indent
from typing import List, Iterable

from ..colors import make_colored, TextStyle
from ..matching import find_matching_field_names
from ..predicates import DefaultEquality
from ..logging import Logger
from ..field import FieldInterface
from .._common import _default_base_tolerance

from ._common import _read_fields_from_file, _bool_to_exit_code
from ._common import _style_as_error, _style_as_warning, _make_list_string, _get_status_string


class _TestTolerance:
    def __init__(self, tolerances: List[str]) -> None:
        self._default_tolerance: float = _default_base_tolerance()
        self._field_tolerances: dict = {}
        for tol_string in tolerances:
            self._update_tolerance(tol_string)

    def get(self, field_name: str) -> float:
        return self._field_tolerances.get(field_name, self._default_tolerance)

    def _update_tolerance(self, tol_string: str) -> None:
        if self._is_field_tolerance_string(tol_string):
            self._update_field_tolerance(tol_string)
        else:
            self._default_tolerance = float(tol_string)

    def _is_field_tolerance_string(self, tol_string: str) -> bool:
        return ":" in tol_string

    def _update_field_tolerance(self, tol_string: str) -> None:
        value = tol_string.split(":")[0]
        field_name = tol_string.split(":")[1]
        self._field_tolerances[field_name] = float(value)


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
        "-i", "--ignore-missing-result-fields",
        required=False,
        action="store_true",
        help="Use this flag to suppress errors from missing result fields"
    )
    parser.add_argument(
        "-m", "--ignore-missing-reference-fields",
        required=False,
        action="store_true",
        help="Use this flag to suppress errors from missing reference fields"
    )
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
    parser.add_argument(
        "--verbosity",
        required=False,
        default=2,
        type=int,
        help="Set the verbosity level"
    )


def _run(args: dict, logger: Logger) -> int:
    if not logger.verbosity_level:
        logger.verbosity_level = args["verbosity"]

    rel_tol_args = args.get("relative_tolerance")
    abs_tol_args = args.get("absolute_tolerance")
    rel_tol = _TestTolerance(rel_tol_args if rel_tol_args is not None else [])
    abs_tol = _TestTolerance(abs_tol_args if abs_tol_args is not None else [])
    passed = _run_file_compare(
        args["file"],
        args["reference"],
        args["ignore_missing_result_fields"],
        args["ignore_missing_reference_fields"],
        logger,
        rel_tol,
        abs_tol
    )
    return _bool_to_exit_code(passed)


def _run_file_compare(res_file: str,
                      ref_file: str,
                      ignore_missing_results: bool,
                      ignore_missing_references: bool,
                      logger: Logger,
                      rel_tol: _TestTolerance = _TestTolerance([]),
                      abs_tol: _TestTolerance = _TestTolerance([])) -> bool:
    try:  # read in results file
        res_fields = _read_fields_from_file(res_file, logger)
    except IOError as e:
        logger.log(_read_error_message(res_file, str(e)), verbosity_level=1)
        return False

    try:  # read in reference file
        ref_fields = _read_fields_from_file(ref_file, logger)
    except IOError as e:
        logger.log(_read_error_message(ref_file, str(e)), verbosity_level=1)
        return False

    match_result = find_matching_field_names(res_fields, ref_fields)
    try:
        passed = _do_field_comparisons(
            res_fields, ref_fields, match_result.matches, logger, rel_tol, abs_tol
        )
    except Exception as e:
        logger.log(f"Could not compare the files. Exception:\n{e}\n", verbosity_level=1)
        return False

    missing_results = match_result.orphan_references
    missing_references = match_result.orphan_results
    _log_missing_results(missing_results, ignore_missing_results, logger)
    _log_missing_references(missing_references, ignore_missing_references, logger)
    passed = False if missing_results and not ignore_missing_results else passed
    passed = False if missing_references and not ignore_missing_references else passed

    logger.log("File comparison {}\n".format(_get_status_string(passed)))
    return passed


def _do_field_comparisons(res_fields: Iterable[FieldInterface],
                          ref_fields: Iterable[FieldInterface],
                          field_names: Iterable[str],
                          logger: Logger,
                          rel_tol: _TestTolerance,
                          abs_tol: _TestTolerance) -> bool:
    res_field_dict: dict = {field.name: field.values for field in res_fields}
    ref_field_dict: dict = {field.name: field.values for field in ref_fields}
    passed = True
    for name in field_names:
        predicate = DefaultEquality(rel_tol=rel_tol.get(name), abs_tol=abs_tol.get(name))
        result = predicate(res_field_dict[name], ref_field_dict[name])
        msg = _get_comparison_message_string(name, bool(result))
        report = _get_predicate_report_string(result.predicate_info, result.report)
        passed = False if not result else passed
        logger.log(msg, verbosity_level=1)
        logger.log(indent(report, " -- "), verbosity_level=2)
    return passed


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
