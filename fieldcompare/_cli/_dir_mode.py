"""Command-line interface for comparing a pair of folders"""

from typing import Iterable, Optional
from argparse import ArgumentParser
from typing import List, Tuple
from os.path import join
from datetime import datetime
from dataclasses import dataclass
from xml.etree.ElementTree import ElementTree, Element

from .._matching import find_matching_file_names
from .._format import as_error, as_warning, highlighted, get_status_string, make_indented_list_string
from .._common import _measure_time

from ._junit import as_junit_xml_element
from ._common import (
    CLILogger,
    _bool_to_exit_code,
    _parse_field_tolerances,
    _log_suite_summary,
    PatternFilter,
    _include_all,
    _exclude_all
)

from ._file_mode import (
    _add_tolerance_options_args,
    _add_field_options_args,
    _add_field_filter_options_args,
    _add_mesh_reorder_options_args,
    _add_junit_export_arg
)

from ._deduce_domain import is_supported_file
from ._test_suite import TestSuite, TestResult, Test
from ._file_comparison import FileComparisonOptions, FileComparison


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
        "--ignore-missing-source-files",
        required=False,
        action="store_true",
        help="Use this flag to suppress errors from missing source files"
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


def _run(args: dict, in_logger: CLILogger) -> int:
    logger = in_logger.with_verbosity(args["verbosity"])

    res_dir = args["dir"]
    ref_dir = args["reference_dir"]
    logger.log("Comparing files in the directories '{}' and '{}'\n\n".format(
        highlighted(res_dir),
        highlighted(ref_dir)),
        verbosity_level=1
    )

    categories = _categorize_files(args, res_dir, ref_dir)
    comparisons = _do_file_comparisons(
        args, categories.files_to_compare, logger
    )

    _log_unhandled_files(args, categories, logger)
    _add_unhandled_comparisons(args, categories, comparisons)

    if args["junit_xml"] is not None:
        suites = Element("testsuites")
        for _, timestamp, suite in comparisons:
            suites.append(as_junit_xml_element(suite, timestamp))
        ElementTree(suites).write(args["junit_xml"], xml_declaration=True)

    logger.log("\n")
    _log_suite_summary(
        list(suite for _, _, suite in comparisons), "file",
        logger.with_modified_verbosity(-1)
    )

    passed = all(comp for _, _, comp in comparisons)
    return _bool_to_exit_code(passed)


@dataclass
class CategorizedFiles:
    files_to_compare: List[str]
    missing_sources: List[str]
    missing_references: List[str]
    filtered_files: List[str]
    unsupported_files: List[str]


def _categorize_files(args: dict, res_dir: str, ref_dir: str) -> CategorizedFiles:
    include_filter = PatternFilter(args["include_files"]) if args["include_files"] else _include_all()

    search_result = find_matching_file_names(res_dir, ref_dir)
    matches = list(n for n, _ in search_result.matches)
    filtered_matches = [m for m in matches if include_filter(m)]
    missing_sources = [m for m in search_result.orphans_in_reference if include_filter(m)]
    missing_references = [m for m in search_result.orphans_in_source if include_filter(m)]

    dropped_matches = list(set(matches).difference(set(filtered_matches)))
    supported_files = list(filter(lambda f: is_supported_file(join(res_dir, f)), filtered_matches))
    unsupported_files = list(set(filtered_matches).difference(set(supported_files)))

    return CategorizedFiles(
        files_to_compare=supported_files,
        missing_sources=missing_sources,
        missing_references=missing_references,
        filtered_files=dropped_matches,
        unsupported_files=unsupported_files
    )


FileComparisons = List[Tuple[str, str, TestSuite]]

def _do_file_comparisons(args,
                         filenames: Iterable[str],
                         logger: CLILogger) -> FileComparisons:
    _rel_tol_map = _parse_field_tolerances(args.get("relative_tolerance"))
    _abs_tol_map = _parse_field_tolerances(args.get("absolute_tolerance"))

    file_comparisons = []
    for i, filename in enumerate(filenames):
        timestamp = datetime.now().isoformat()
        res_file = join(args["dir"], filename)
        ref_file = join(args["reference_dir"], filename)

        logger.log(("\n" if i > 0 else ""), verbosity_level=1)
        logger.log(
            f"Comparing '{highlighted(res_file)}'\n"
            f"      and '{highlighted(ref_file)}'\n",
            verbosity_level=1
        )

        opts = FileComparisonOptions(
            ignore_missing_source_fields=args["ignore_missing_source_fields"],
            ignore_missing_reference_fields=args["ignore_missing_reference_fields"],
            ignore_missing_sequence_steps=args["ignore_missing_sequence_steps"],
            relative_tolerances=_rel_tol_map,
            absolute_tolerances=_abs_tol_map,
            field_inclusion_filter=PatternFilter(args["include_fields"]) if args["include_fields"] else _include_all(),
            field_exclusion_filter=PatternFilter(args["exclude_fields"]) if args["exclude_fields"] else _exclude_all(),
            disable_mesh_reordering=True if args["disable_mesh_reordering"] else False,
            disable_unconnected_points_removal=True if args["disable_mesh_orphan_point_removal"] else False
        )
        try:
            sub_logger = logger.with_prefix("  ")
            comparator = FileComparison(opts, sub_logger.with_modified_verbosity(-1))
            cpu_time, test_suite = _measure_time(comparator)(res_file, ref_file)
            file_comparisons.append((filename, timestamp, test_suite.with_overridden(
                cpu_time=cpu_time,
                name=res_file,
                shortlog=_get_failing_field_test_names(test_suite)
            )))
            sub_logger.log(
                f"File comparison {get_status_string(bool(test_suite))}\n", verbosity_level=1
            )
        except Exception as e:
            output = f"Error upon file comparison: {str(e)}"
            logger.log(output, verbosity_level=1)
            file_comparisons.append((
                filename,
                timestamp,
                TestSuite(
                    tests=[],
                    name=filename,
                    result=TestResult.error,
                    shortlog="Exception raised",
                    stdout=output
                )
            ))

    return file_comparisons


def _get_failing_field_test_names(test_suite: TestSuite) -> Optional[str]:
    names = [t.name for t in test_suite if not t.result]
    if not names:
        return None

    names_string = ""
    max_num_characters = 30
    for n in names:
        n = f"'{n}'"
        if len(names_string) + len(n) > max_num_characters:
            return names_string
        names_string = n if not names_string else ";".join([names_string, n])
    return names_string


def _log_unhandled_files(args, categories, logger) -> None:
    _log_unhandled_file_list(
        _missing_res_or_ref_message("result", not args["ignore_missing_source_files"]),
        categories.missing_sources,
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
                             logger: CLILogger,
                             verbosity_level: int) -> None:
    if names:
        logger.log(
            f"\n{message}\n{make_indented_list_string(names)}\n",
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
        categories.missing_sources,
        "Missing source file",
        not args["ignore_missing_source_files"]
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
    status = TestResult.failed if treat_as_failure else TestResult.skipped
    for name in names:
        # insert a dummy testcase such that junit readers show a (skipped/failed) test
        suite = TestSuite(
            tests=[Test("file comparison", status, shortlog=reason, stdout="", cpu_time=None)],
            name=name,
            result=status,
            shortlog=reason
        )
        comparisons.append((name, datetime.now().isoformat(), suite))
