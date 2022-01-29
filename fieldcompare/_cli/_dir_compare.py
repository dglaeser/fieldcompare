"""Command-line interface for comparing a pair of folders"""

from argparse import ArgumentParser
from os.path import join

from ..matching import find_matching_file_names
from ..logging import Logger, ModifiedVerbosityLoggerFacade, IndentedLoggingFacade
from ..field_io import is_supported_file
from .._common import _style_text, TextStyle

from ._common import _bool_to_exit_code
from ._common import _style_as_error, _style_as_warning, _make_list_string, _get_status_string
from ._file_compare import _run_file_compare


def _add_arguments(parser: ArgumentParser):
    parser.add_argument(
        "dir",
        type=str,
        help="The directory containing the fieles to be compared against references"
    )
    parser.add_argument(
        "-r", "--reference-dir",
        required=True,
        type=str,
        help="The directory with the reference files"
    )
    parser.add_argument(
        "-i", "--ignore-missing-result-files",
        required=False,
        action="store_true",
        help="Use this flag to suppress errors from missing result files"
    )
    parser.add_argument(
        "-if", "--ignore-missing-result-fields",
        required=False,
        action="store_true",
        help="Use this flag to suppress errors from missing result fields"
    )
    parser.add_argument(
        "-m", "--ignore-missing-reference-files",
        required=False,
        action="store_true",
        help="Use this flag to suppress errors from missing reference files"
    )
    parser.add_argument(
        "-mf", "--ignore-missing-reference-fields",
        required=False,
        action="store_true",
        help="Use this flag to suppress errors from missing reference fields"
    )
    parser.add_argument(
        "--verbosity",
        required=False,
        default=3,
        type=int,
        help="Set the verbosity level"
    )


def _run(args: dict, logger: Logger) -> int:
    if not logger.verbosity_level:
        logger.verbosity_level = args["verbosity"]

    res_dir = args["dir"]
    ref_dir = args["reference_dir"]
    search_result = find_matching_file_names(res_dir, ref_dir)
    logger.log("Comparing the files in the directories '{}' and '{}'\n".format(
        _style_text(res_dir, style=TextStyle.bright),
        _style_text(ref_dir, style=TextStyle.bright)),
        verbosity_level=1
    )
    if logger.verbosity_level and logger.verbosity_level == 1:
        logger.log("\n")

    passed = True

    # Use decreased verbosity level in the file comparisons
    # s.t. level=1 does not include all the file-test output
    lower_verbosity_logger = ModifiedVerbosityLoggerFacade(logger, verbosity_change=-1)
    indented_logger = IndentedLoggingFacade(lower_verbosity_logger, first_line_prefix=" "*4)
    for match in filter(lambda f: is_supported_file(join(res_dir, f)), search_result.matches):
        res_file = join(res_dir, match)
        ref_file = join(ref_dir, match)

        if logger.verbosity_level and logger.verbosity_level > 1:
            logger.log("\n")
        logger.log("Comparing the files '{}' and '{}'\n".format(
            _style_text(res_file, style=TextStyle.bright),
            _style_text(ref_file, style=TextStyle.bright)),
            verbosity_level=1
        )

        _passed = _run_file_compare(
            res_file,
            ref_file,
            args["ignore_missing_result_fields"],
            args["ignore_missing_reference_fields"],
            indented_logger
        )
        passed = False if not _passed else passed

    orphan_results = search_result.orphan_results
    if orphan_results:
        should_fail = not args["ignore_missing_reference_files"]
        passed = False if should_fail else passed
        logger.log(
            "\n{}:\n".format(_missing_res_or_ref_message("reference", should_fail)),
            verbosity_level=1
        )
        logger.log(
            "{}\n".format(_make_list_string([join(ref_dir, f) for f in orphan_results])),
            verbosity_level=1
        )

    orphan_references = search_result.orphan_references
    if orphan_references:
        should_fail = not args["ignore_missing_result_files"]
        passed = False if should_fail else passed
        logger.log(
            "\n{}:\n".format(_missing_res_or_ref_message("result", should_fail)),
            verbosity_level=1
        )
        logger.log(
            "{}\n".format(_make_list_string([join(res_dir, f) for f in orphan_references])),
            verbosity_level=1
        )

    unsupported_files = list(filter(
        lambda f: not is_supported_file(join(res_dir, f)),
        search_result.matches
    ))
    if unsupported_files:
        logger.log(
            "\nThe following files have been skipped due to unsupported format:\n{}\n".format(
                _make_list_string([join(res_dir, f) for f in unsupported_files])
            ),
            verbosity_level=2
        )

    logger.log("\nDirectory comparison {}\n".format(_get_status_string(passed)))
    return _bool_to_exit_code(passed)


def _missing_res_or_ref_message(res_or_ref: str, is_error: bool) -> str:
    result = f"missing {res_or_ref} files"
    if is_error:
        result = "Could not process " + _style_as_error(result)
    else:
        result = "Ignored the following " + _style_as_warning(result)
    return result
