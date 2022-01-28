"""Command-line interface for comparing a pair of files"""

from argparse import ArgumentParser
from textwrap import indent

from ..compare import compare_matching_fields_equal, ComparisonLog
from ..logging import Logger

from ._common import _read_fields_from_file, _bool_to_exit_code
from ._common import _get_comparison_message_string, _get_predicate_report_string
from ._common import _get_missing_results, _get_missing_references
from ._common import _style_as_error, _style_as_warning, _make_list_string, _get_status_string


class ComparisonLogCallBack:
    def __init__(self, logger: Logger) -> None:
        self._logger = logger

    def __call__(self, comparison_log: ComparisonLog) -> None:
        self._logger.log(_get_comparison_message_string(comparison_log), verbosity_level=1)
        self._logger.log(
            indent(_get_predicate_report_string(comparison_log), " -- "),
            verbosity_level=2
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


def _run(args: dict, logger: Logger) -> int:
    passed = _run_file_compare(
        args["file"],
        args["reference"],
        args["ignore_missing_result_fields"],
        args["ignore_missing_reference_fields"],
        logger
    )
    return _bool_to_exit_code(passed)


def _run_file_compare(res_file: str,
                      ref_file: str,
                      ignore_missing_results: bool,
                      ignore_missing_references: bool,
                      logger: Logger) -> bool:
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

    try:  # do actual comparison
        comparisons, skips = compare_matching_fields_equal(
            res_fields, ref_fields, ComparisonLogCallBack(logger)
        )
    except Exception as e:
        logger.log(f"Could not compare the files. Exception:\n{e}\n", verbosity_level=1)
        return False

    passed = bool(comparisons)
    missing_results = _get_missing_results(skips)
    if missing_results:
        should_fail = not ignore_missing_results
        passed = False if should_fail else passed
        logger.log(
            "{}\n".format(_missing_res_or_ref_message("result", should_fail)),
            verbosity_level=1
        )
        logger.log(
            "{}\n".format(_make_list_string([str(r.result_field_name) for r in missing_results])),
            verbosity_level=1
        )

    missing_references = _get_missing_references(skips)
    if missing_references:
        should_fail = not ignore_missing_references
        passed = False if should_fail else passed
        logger.log(
            "{}\n".format(_missing_res_or_ref_message("reference", should_fail)),
            verbosity_level=1
        )
        logger.log(
            "{}\n".format(_make_list_string([str(r.result_field_name) for r in missing_references])),
            verbosity_level=1
        )

    logger.log("File comparison {}\n".format(_get_status_string(passed)))
    return passed


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
