"""Command-line interface for comparing a pair of folders"""

from typing import Iterable
from argparse import ArgumentParser
from typing import List, Tuple
from os.path import join
from datetime import datetime
from dataclasses import dataclass
from xml.etree.ElementTree import ElementTree, Element

from .._matching import find_matching_file_names
from .._logging import LoggerInterface, ModifiedVerbosityLogger, IndentedLogger
from .._colors import make_colored, TextStyle
from .._comparison import ComparisonSuite, Comparison, Status
from .._file_comparison import FileComparisonOptions
from .._format import as_error, as_warning, get_status_string, make_indented_list_string
from .._common import _measure_time
from .._field_io import is_supported_file

from ._junit import TestSuite
from ._common import (
    _bool_to_exit_code,
    _parse_field_tolerances,
    _run_file_compare,
    _log_summary,
    PatternFilter,
    _include_all,
    _exclude_all
)

from ._file_compare import (
    _add_tolerance_options_args,
    _add_field_options_args,
    _add_field_filter_options_args,
    _add_mesh_reorder_options_args,
    _add_junit_export_arg
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
        help="Pass a Unix-style wildcard pattern to filter files to be compared. This option can "
             "be used multiple times. Files that match any of the patterns are considered. "
             "If this option is not specified, all files found in the directories are considered."
    )
    parser.add_argument(
        "--verbosity",
        required=False,
        default=2,
        type=int,
        help="Set the verbosity level"
    )
    _add_field_options_args(parser)
    _add_field_filter_options_args(parser)
    _add_tolerance_options_args(parser)
    _add_mesh_reorder_options_args(parser)
    _add_junit_export_arg(parser)


def _run(args: dict, logger: LoggerInterface) -> int:
    logger.verbosity_level = args["verbosity"]

    res_dir = args["dir"]
    ref_dir = args["reference_dir"]
    logger.log("Comparing files in the directories '{}' and '{}'\n\n".format(
        make_colored(res_dir, style=TextStyle.bright),
        make_colored(ref_dir, style=TextStyle.bright)),
        verbosity_level=1
    )

    categories = _categorize_files(args, res_dir, ref_dir)
    cpu_time, comparisons = _measure_time(_do_file_comparisons)(args, categories.files_to_compare, logger)

    logger.log("\n", verbosity_level=1)
    _log_unhandled_files(args, categories, logger)
    _add_unhandled_comparisons(args, categories, comparisons)

    if args["junit_xml"] is not None:
        suites = Element("testsuites")
        for suite_name, timestamp, suite in comparisons:
            test_suite = TestSuite(suite_name, suite, timestamp, cpu_time)
            suites.append(test_suite.as_xml())
        ElementTree(suites).write(args["junit_xml"], xml_declaration=True)

    def test_details_callback(_name: str) -> str:
        for _, _, suite in filter(lambda tup: tup[0] == _name, comparisons):
            if suite.stdout:
                return f"'{suite.stdout}'"
            if suite.status == Status.failed:
                return ",".join(f"'{comp.name}'" for comp in suite if comp.status == Status.failed)
        return ""

    logger.log("\n")
    _log_summary(
        logger,
        [name for name, _, comp in comparisons if comp.status == Status.passed],
        [name for name, _, comp in comparisons if not comp],
        [name for name, _, comp in comparisons if comp.status == Status.skipped],
        "file",
        verbosity_level=1,
        test_details_callback=test_details_callback
    )

    passed = all(comp for _, _, comp in comparisons)
    logger.log("\nDirectory comparison {}\n".format(get_status_string(passed)))
    return _bool_to_exit_code(passed)


@dataclass
class CategorizedFiles:
    files_to_compare: List[str]
    missing_results: List[str]
    missing_references: List[str]
    filtered_files: List[str]
    unsupported_files: List[str]


def _categorize_files(args: dict, res_dir: str, ref_dir: str) -> CategorizedFiles:
    include_filter = PatternFilter(args["include_files"]) if args["include_files"] else _include_all()

    search_result = find_matching_file_names(res_dir, ref_dir)
    filtered_matches = include_filter(search_result.matches)
    missing_results = include_filter(search_result.orphan_references)
    missing_references = include_filter(search_result.orphan_results)

    dropped_matches = list(set(search_result.matches).difference(set(filtered_matches)))
    supported_files = list(filter(lambda f: is_supported_file(join(res_dir, f)), filtered_matches))
    unsupported_files = list(set(filtered_matches).difference(set(supported_files)))

    return CategorizedFiles(
        files_to_compare=supported_files,
        missing_results=missing_results,
        missing_references=missing_references,
        filtered_files=dropped_matches,
        unsupported_files=unsupported_files
    )


FileComparisons = List[Tuple[str, str, ComparisonSuite]]

def _do_file_comparisons(args,
                         filenames: Iterable[str],
                         logger: LoggerInterface) -> FileComparisons:
    _sub_indent = " "*4
    _quiet_logger = ModifiedVerbosityLogger(logger, verbosity_change=-1)
    _sub_logger = IndentedLogger(_quiet_logger, first_line_prefix=_sub_indent)
    _rel_tol_map = _parse_field_tolerances(args.get("relative_tolerance"))
    _abs_tol_map = _parse_field_tolerances(args.get("absolute_tolerance"))

    file_comparisons = []
    for i, filename in enumerate(filenames):
        timestamp = datetime.now().isoformat()
        res_file = join(args["dir"], filename)
        ref_file = join(args["reference_dir"], filename)

        logger.log(("\n" if i > 0 else ""), verbosity_level=1)
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
            field_inclusion_filter=PatternFilter(args["include_fields"]) if args["include_fields"] else _include_all(),
            field_exclusion_filter=PatternFilter(args["exclude_fields"]) if args["exclude_fields"] else _exclude_all(),
            disable_mesh_reordering=True if args["disable_mesh_reordering"] else False,
            disable_mesh_ghost_point_removal=True if args["disable_mesh_ghost_point_removal"] else False
        )
        try:
            field_comparisons = _run_file_compare(_sub_logger, opts, res_file, ref_file)
            file_comparisons.append((filename, timestamp, field_comparisons))
            IndentedLogger(logger, first_line_prefix=_sub_indent).log(
                f"File comparison {get_status_string(bool(field_comparisons))}\n", verbosity_level=1
            )
        except Exception as e:
            logger.log(str(e), verbosity_level=1)
            file_comparisons.append((filename, timestamp, ComparisonSuite(Status.error, str(e))))

    return file_comparisons


def _log_unhandled_files(args, categories, logger) -> None:
    _log_unhandled_file_list(
        _missing_res_or_ref_message("result", not args["ignore_missing_result_files"]),
        categories.missing_results,
        logger,
        verbosity_level=1
    )
    _log_unhandled_file_list(
        _missing_res_or_ref_message("reference", not args["ignore_missing_reference_files"]),
        categories.missing_references,
        logger,
        verbosity_level=1
    )
    _log_unhandled_file_list(
        as_warning("The following files have been skipped due to unsupported format:"),
        categories.unsupported_files,
        logger,
        verbosity_level=2
    )
    _log_unhandled_file_list(
        as_warning("The following files have been filtered out by the wildcard patterns:"),
        categories.filtered_files,
        logger,
        verbosity_level=3
    )


def _log_unhandled_file_list(message: str,
                             names: List[str],
                             logger: LoggerInterface,
                             verbosity_level: int) -> None:
    if names:
        logger.log(
            f"{message}\n{make_indented_list_string(names)}\n",
            verbosity_level=verbosity_level
        )


def _missing_res_or_ref_message(res_or_ref: str, is_error: bool) -> str:
    result = f"missing {res_or_ref} files"
    if is_error:
        result = "Could not process " + as_error(result)
    else:
        result = "Ignored " + as_warning(result)
    return result


def _add_unhandled_comparisons(args: dict,
                               categories: CategorizedFiles,
                               comparisons: FileComparisons) -> None:
    _add_skipped_file_comparisons(
        comparisons,
        categories.missing_results,
        "Missing result file",
        not args["ignore_missing_result_files"]
    )
    _add_skipped_file_comparisons(
        comparisons,
        categories.missing_references,
        "Missing reference file",
        not args["ignore_missing_reference_files"]
    )
    _add_skipped_file_comparisons(
        comparisons,
        categories.unsupported_files,
        "Unsupported file format"
    )
    _add_skipped_file_comparisons(
        comparisons,
        categories.filtered_files,
        "Filtered out by given wildcard patterns"
    )


def _add_skipped_file_comparisons(comparisons: FileComparisons,
                                  names: List[str],
                                  reason: str,
                                  treat_as_failure: bool = False):
    status = Status.failed if treat_as_failure else Status.skipped
    for name in names:
        suite = ComparisonSuite(status, reason)
        # insert a dummy testcase such that junit readers show a (skipped/failed) test
        suite.insert(Comparison("file comparison", status, reason))
        comparisons.append((name, datetime.now().isoformat(), suite))
