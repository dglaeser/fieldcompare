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
        "-i", "--ignore-missing-results",
        required=False,
        action="store_true",
        help="Use this flag to suppress errors from missing result fields"
    )
    parser.add_argument(
        "-m", "--ignore-missing-references",
        required=False,
        action="store_true",
        help="Use this flag to suppress errors from missing reference fields"
    )


def _run(args: dict, logger: Logger) -> int:
    passed = _run_file_compare(
        args["file"],
        args["reference"],
        args["ignore_missing_results"],
        args["ignore_missing_references"],
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
        logger.log(f"An error occurred when reading {res_file}: {e}", verbosity_level=1)
        return False

    try:  # read in reference file
        ref_fields = _read_fields_from_file(ref_file, logger)
    except IOError as e:
        logger.log(f"An error occurred when reading {ref_file}: {e}", verbosity_level=1)
        return False

    try:  # do actual comparison
        comparisons, skips = compare_matching_fields_equal(
            res_fields, ref_fields, ComparisonLogCallBack(logger)
        )
    except Exception as e:
        logger.log(f"Could not compare the files. Exception:\n{e}", verbosity_level=1)
        return False

    passed = bool(comparisons)
    missing_results = _get_missing_results(skips)
    if missing_results:
        not_been_found = _style_as_warning("not been found")
        if not ignore_missing_results:
            passed = False
            not_been_found = _style_as_error(not_been_found)
        logger.log(
            f"The following reference fields have {not_been_found} in the results:\n",
            verbosity_level=1
        )
        logger.log(
            _make_list_string([str(r.reference_field_name) for r in missing_results]),
            verbosity_level=1
        )

    missing_references = _get_missing_references(skips)
    if missing_references:
        not_been_found = _style_as_warning("not been found")
        if ignore_missing_references:
            passed = False
            not_been_found = _style_as_error(not_been_found)
        logger.log(
            f"The following result fields have {not_been_found} in the references:\n",
            verbosity_level=1
        )
        logger.log(
            _make_list_string([str(r.result_field_name) for r in missing_references]),
            verbosity_level=1
        )

    logger.log("File comparison {}\n".format(_get_status_string(passed)))
    return passed
