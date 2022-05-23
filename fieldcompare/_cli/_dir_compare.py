"""Command-line interface for comparing a pair of folders"""

from typing import Iterable
from argparse import ArgumentParser
from typing import List
from os.path import join

from .._matching import find_matching_file_names
from .._logging import LoggerInterface, ModifiedVerbosityLogger, IndentedLogger
from .._colors import make_colored, TextStyle
from .._file_comparison import FileComparisonOptions
from .._format import as_error, as_warning, make_list_string, get_status_string

from .._field_io import is_supported_file
from ._common import (
    _bool_to_exit_code,
    _parse_field_tolerances,
    _run_file_compare,
    RegexFilter
)

from ._file_compare import (
    _add_tolerance_options_args,
    _add_field_options_args,
    _add_field_filter_options_args,
    _add_mesh_reorder_options_args
)


def _add_arguments(parser: ArgumentParser):
    parser.add_argument(
        "dir",
        type=str,
        help="The directory containing the files to be compared against references"
    )
    parser.add_argument(
        "-r", "--reference-dir",
        required=True,
        type=str,
        help="The directory with the reference files"
    )
    parser.add_argument(
        "--ignore-missing-result-files",
        required=False,
        action="store_true",
        help="Use this flag to suppress errors from missing result files"
    )
    parser.add_argument(
        "--ignore-missing-reference-files",
        required=False,
        action="store_true",
        help="Use this flag to suppress errors from missing reference files"
    )
    parser.add_argument(
        "--include-files",
        required=False,
        action="append",
        help="Pass a regular expression used to filter files to be compared. This option can "
             "be used multiple times. Files that match any of the patterns are considered. "
             "If this option is not specified, all files found in the directories are considered."
    )
    parser.add_argument(
        "--verbosity",
        required=False,
        default=3,
        type=int,
        help="Set the verbosity level"
    )
    _add_field_options_args(parser)
    _add_field_filter_options_args(parser)
    _add_tolerance_options_args(parser)
    _add_mesh_reorder_options_args(parser)


def _run(args: dict, logger: LoggerInterface) -> int:
    logger.verbosity_level = args["verbosity"]

    res_dir = args["dir"]
    ref_dir = args["reference_dir"]
    search_result = find_matching_file_names(res_dir, ref_dir)
    logger.log("Comparing files in the directories '{}' and '{}'\n\n".format(
        make_colored(res_dir, style=TextStyle.bright),
        make_colored(ref_dir, style=TextStyle.bright)),
        verbosity_level=1
    )

    include_filter = RegexFilter(args["include_files"] if args["include_files"] else ["*"])
    filtered_matches = include_filter(search_result.matches)
    missing_results = include_filter(search_result.orphan_references)
    missing_references = include_filter(search_result.orphan_results)

    supported_files = list(filter(lambda f: is_supported_file(join(res_dir, f)), filtered_matches))
    unsupported_files = list(filter(lambda f: not is_supported_file(join(res_dir, f)), filtered_matches))
    dropped_matches = list(filter(lambda f: f not in filtered_matches, search_result.matches))

    passed = _do_file_comparisons(args, supported_files, logger)
    _log_missing_results(args, missing_results, logger)
    _log_missing_references(args, missing_references, logger)
    passed = False if missing_results and not args["ignore_missing_result_files"] else passed
    passed = False if missing_references and not args["ignore_missing_reference_files"] else passed

    if unsupported_files:
        logger.log(
            "The following files have been skipped due to unsupported format:\n{}\n".format(
                make_list_string([join(res_dir, f) for f in unsupported_files])
            ),
            verbosity_level=2
        )

    if dropped_matches:
        logger.log(
            "\nThe following files have been filtered out by the given regular expressions:\n{}\n".format(
                make_list_string([join(res_dir, f) for f in dropped_matches])
            ),
            verbosity_level=2
        )

    logger.log("\nDirectory comparison {}\n".format(get_status_string(passed)))
    return _bool_to_exit_code(passed)


def _do_file_comparisons(args,
                         filenames: Iterable[str],
                         logger: LoggerInterface) -> bool:
    passed = True
    _sub_indent = " "*4
    _quiet_logger = ModifiedVerbosityLogger(logger, verbosity_change=-1)
    _sub_logger = IndentedLogger(_quiet_logger, first_line_prefix=_sub_indent)
    _rel_tol_map = _parse_field_tolerances(args.get("relative_tolerance"))
    _abs_tol_map = _parse_field_tolerances(args.get("absolute_tolerance"))
    for filename in filenames:
        res_file = join(args["dir"], filename)
        ref_file = join(args["reference_dir"], filename)
        logger.log("Comparing the files '{}' and '{}'\n".format(
            make_colored(res_file, style=TextStyle.bright),
            make_colored(ref_file, style=TextStyle.bright)),
            verbosity_level=1
        )

        opts = FileComparisonOptions(
            ignore_missing_result_fields=args["ignore_missing_result_fields"],
            ignore_missing_reference_fields=args["ignore_missing_reference_fields"],
            relative_tolerances=_rel_tol_map,
            absolute_tolerances=_abs_tol_map,
            field_inclusion_filter=RegexFilter(args["include_fields"] if args["include_fields"] else ["*"]),
            field_exclusion_filter=RegexFilter(args["exclude_fields"]),
            disable_mesh_reordering=True if args["disable_mesh_reordering"] else False
        )
        try:
            _passed = _run_file_compare(_sub_logger, opts, res_file, ref_file)
            IndentedLogger(logger, first_line_prefix=_sub_indent).log(
                f"File comparison {get_status_string(_passed)}\n", verbosity_level=1
            )
        except Exception as e:
            logger.log(str(e), verbosity_level=1)
            _passed = False

        logger.log("\n", verbosity_level=1)
        passed = False if not _passed else passed
    return passed


def _log_missing_results(args, filenames: List[str], logger: LoggerInterface) -> None:
    if filenames:
        should_fail = not args["ignore_missing_result_files"]
        logger.log(
            "\n{}:\n".format(_missing_res_or_ref_message("result", should_fail)),
            verbosity_level=1
        )
        logger.log(
            "{}\n".format(make_list_string([join(args["dir"], f) for f in filenames])),
            verbosity_level=1
        )


def _log_missing_references(args, filenames: List[str], logger: LoggerInterface) -> None:
    if filenames:
        should_fail = not args["ignore_missing_reference_files"]
        logger.log(
            "\n{}:\n".format(_missing_res_or_ref_message("reference", should_fail)),
            verbosity_level=1
        )
        logger.log(
            "{}\n".format(make_list_string([join(args["reference_dir"], f) for f in filenames])),
            verbosity_level=1
        )


def _missing_res_or_ref_message(res_or_ref: str, is_error: bool) -> str:
    result = f"missing {res_or_ref} files"
    if is_error:
        result = "Could not process " + as_error(result)
    else:
        result = "Ignored the following " + as_warning(result)
    return result
