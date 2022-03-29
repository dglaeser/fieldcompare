"""Command-line interface for comparing a pair of folders"""

from typing import Iterable
from argparse import ArgumentParser
from typing import List
from os.path import join

from ..matching import find_matching_file_names
from ..logging import Logger, ModifiedVerbosityLoggerFacade, IndentedLoggingFacade
from ..field_io import is_supported_file
from ..colors import make_colored, TextStyle

from ._common import _bool_to_exit_code, _parse_field_tolerances, InclusionFilter, ExclusionFilter
from ._common import _style_as_error, _style_as_warning, _make_list_string, _get_status_string

from ._file_compare import _add_tolerance_options_args, _add_field_options_args, _add_field_filter_options_args
from ._file_compare import FileComparison, FileComparisonOptions


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


def _run(args: dict, logger: Logger) -> int:
    if not logger.verbosity_level:
        logger.verbosity_level = args["verbosity"]

    res_dir = args["dir"]
    ref_dir = args["reference_dir"]
    search_result = find_matching_file_names(res_dir, ref_dir)
    logger.log("Comparing files in the directories '{}' and '{}'\n\n".format(
        make_colored(res_dir, style=TextStyle.bright),
        make_colored(ref_dir, style=TextStyle.bright)),
        verbosity_level=1
    )

    filtered_matches = InclusionFilter(args["include_files"])(search_result.matches)

    supported_files = list(filter(lambda f: is_supported_file(join(res_dir, f)), filtered_matches))
    unsupported_files = list(filter(lambda f: not is_supported_file(join(res_dir, f)), filtered_matches))
    dropped_matches = list(filter(lambda f: f not in filtered_matches, search_result.matches))
    missing_results = search_result.orphan_references
    missing_references = search_result.orphan_results

    passed = _do_file_comparisons(args, supported_files, logger)
    _log_missing_results(args, missing_results, logger)
    _log_missing_references(args, missing_references, logger)
    passed = False if missing_results and not args["ignore_missing_result_files"] else passed
    passed = False if missing_references and not args["ignore_missing_reference_files"] else passed

    if unsupported_files:
        logger.log(
            "The following files have been skipped due to unsupported format:\n{}\n".format(
                _make_list_string([join(res_dir, f) for f in unsupported_files])
            ),
            verbosity_level=2
        )

    if dropped_matches:
        logger.log(
            "\nThe following files have been filtered out by the given regular expressions:\n{}\n".format(
                _make_list_string([join(res_dir, f) for f in dropped_matches])
            ),
            verbosity_level=2
        )

    logger.log("\nDirectory comparison {}\n".format(_get_status_string(passed)))
    return _bool_to_exit_code(passed)


def _do_file_comparisons(args,
                         filenames: Iterable[str],
                         logger: Logger) -> bool:
    passed = True
    _quiet_logger = ModifiedVerbosityLoggerFacade(logger, verbosity_change=-1)
    _sub_logger = IndentedLoggingFacade(_quiet_logger, first_line_prefix=" "*4)
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
            field_inclusion_filter=InclusionFilter(args["include_fields"]),
            field_exclusion_filter=ExclusionFilter(args["exclude_fields"])
        )
        try:
            comparison = FileComparison(res_file, ref_file, opts, _sub_logger)
            _passed = comparison.run()
        except Exception as e:
            logger.log(str(e), verbosity_level=1)
            _passed = False

        if _sub_logger.verbosity_level is not None and _sub_logger.verbosity_level == 0:
            logger.log(
                " "*4 + f"File comparison {_get_status_string(_passed)}",
                verbosity_level=1
            )
        logger.log("\n", verbosity_level=1)

        passed = False if not _passed else passed
    return passed


def _log_missing_results(args, filenames: List[str], logger: Logger) -> None:
    if filenames:
        should_fail = not args["ignore_missing_result_files"]
        logger.log(
            "\n{}:\n".format(_missing_res_or_ref_message("result", should_fail)),
            verbosity_level=1
        )
        logger.log(
            "{}\n".format(_make_list_string([join(args["dir"], f) for f in filenames])),
            verbosity_level=1
        )


def _log_missing_references(args, filenames: List[str], logger: Logger) -> None:
    if filenames:
        should_fail = not args["ignore_missing_reference_files"]
        logger.log(
            "\n{}:\n".format(_missing_res_or_ref_message("reference", should_fail)),
            verbosity_level=1
        )
        logger.log(
            "{}\n".format(_make_list_string([join(args["reference_dir"], f) for f in filenames])),
            verbosity_level=1
        )


def _missing_res_or_ref_message(res_or_ref: str, is_error: bool) -> str:
    result = f"missing {res_or_ref} files"
    if is_error:
        result = "Could not process " + _style_as_error(result)
    else:
        result = "Ignored the following " + _style_as_warning(result)
    return result
