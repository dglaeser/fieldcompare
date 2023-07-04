# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Command-line interface for comparing a pair of folders"""

from __future__ import annotations
from typing import Iterable, List, Tuple
from argparse import ArgumentParser
from os.path import join, isdir
from datetime import datetime
from dataclasses import dataclass
from xml.etree.ElementTree import ElementTree, Element

from .._matching import find_matching_file_names
from .._format import highlighted, get_status_string
from .._common import _measure_time
from ..io import is_supported

from ._junit import as_junit_xml_element
from ._common import (
    CLILogger,
    PatternFilter,
    _bool_to_exit_code,
    _parse_field_tolerances,
    _log_suite_summary,
    _include_all,
    _exclude_all,
    _make_file_type_map,
)

from ._file_mode import (
    _add_tolerance_options_args,
    _add_field_options_args,
    _add_field_filter_options_args,
    _add_mesh_reorder_options_args,
    _add_junit_export_arg,
    _add_reader_selection_options_args,
    _add_diff_output_options_args,
)

from ._test_suite import TestSuite, TestResult, TestStatus
from ._file_comparison import FileComparisonOptions, FileComparison, _suite_name


def _add_arguments(parser: ArgumentParser):
    parser.add_argument(
        "source-dir", type=str, help="The directory containing the files to be compared against references"
    )
    parser.add_argument("reference-dir", type=str, help="The directory with the reference files")
    parser.add_argument(
        "--ignore-missing-source-files",
        required=False,
        action="store_true",
        help="Use this flag to suppress errors from missing source files",
    )
    parser.add_argument(
        "--ignore-missing-reference-files",
        required=False,
        action="store_true",
        help="Use this flag to suppress errors from missing reference files",
    )
    parser.add_argument(
        "--include-files",
        required=False,
        action="append",
        help="Pass a Unix-style wildcard pattern to filter files to be compared. This option can "
        "be used multiple times. Files that match any of the patterns are considered. "
        "If this option is not specified, all files found in the directories are considered.",
    )
    parser.add_argument("--verbosity", required=False, default=2, type=int, help="Set the verbosity level")
    _add_field_options_args(parser)
    _add_field_filter_options_args(parser)
    _add_tolerance_options_args(parser)
    _add_mesh_reorder_options_args(parser)
    _add_junit_export_arg(parser)
    _add_reader_selection_options_args(parser)
    _add_diff_output_options_args(parser)


def _run(args: dict, in_logger: CLILogger) -> int:
    logger = in_logger.with_verbosity(args["verbosity"])

    res_dir = args["source-dir"]
    ref_dir = args["reference-dir"]

    def _check_if_is_dir(_dir: str) -> bool:
        _isdir = isdir(_dir)
        if not _isdir:
            logger.log(f"Error: '{_dir}' is not a valid directory\n", verbosity_level=1)
        return _isdir

    if not _check_if_is_dir(res_dir):
        return _bool_to_exit_code(False)
    if not _check_if_is_dir(ref_dir):
        return _bool_to_exit_code(False)

    logger.log(
        "Comparing files in the directories '{}' and '{}'\n\n".format(highlighted(res_dir), highlighted(ref_dir)),
        verbosity_level=1,
    )

    categories = _categorize_files(args, res_dir, ref_dir)
    comparisons = _do_file_comparisons(args, categories.files_to_compare, logger)

    _add_unhandled_comparisons(args, categories, comparisons)

    if args["junit_xml"] is not None:
        suites = Element("testsuites")
        suites.extend([as_junit_xml_element(suite, timestamp) for _, timestamp, suite in comparisons])
        ElementTree(suites).write(args["junit_xml"], xml_declaration=True)

    # create a test suite of test suites for printing a summary
    test_suite = TestSuite(
        [
            TestResult(
                name=suite.name,
                status=suite.status,
                shortlog=suite.shortlog,
                stdout=suite.stdout,
                cpu_time=suite.cpu_time,
            )
            for _, _, suite in comparisons
        ]
    )

    logger.log("\n")
    _log_suite_summary(test_suite, "file", logger)

    passed = all(comp for _, _, comp in comparisons)
    return _bool_to_exit_code(passed)


@dataclass
class CategorizedFiles:
    files_to_compare: list[str]
    missing_sources: list[str]
    missing_references: list[str]
    filtered_files: list[str]
    unsupported_files: list[str]


def _categorize_files(args: dict, res_dir: str, ref_dir: str) -> CategorizedFiles:
    include_filter = PatternFilter(args["include_files"]) if args["include_files"] else _include_all()
    file_type_map = _make_file_type_map(args.get("read_as", []))

    search_result = find_matching_file_names(res_dir, ref_dir)
    matches = list(n for n, _ in search_result.matches)
    filtered_matches = [m for m in matches if include_filter(m)]
    missing_sources = [m for m in search_result.orphans_in_reference if include_filter(m)]
    missing_references = [m for m in search_result.orphans_in_source if include_filter(m)]

    dropped_matches = list(set(matches).difference(set(filtered_matches)))
    supported_files = list(filter(lambda f: is_supported(join(res_dir, f)), filtered_matches))
    unsupported_files = list(set(filtered_matches).difference(set(supported_files)))
    mapped_unsupported_files = [filename for filename in unsupported_files if file_type_map(filename) is not None]
    unsupported_files = list(set(unsupported_files).difference(set(mapped_unsupported_files)))

    return CategorizedFiles(
        files_to_compare=supported_files + mapped_unsupported_files,
        missing_sources=missing_sources,
        missing_references=missing_references,
        filtered_files=dropped_matches,
        unsupported_files=unsupported_files,
    )


FileComparisons = List[Tuple[str, str, TestSuite]]  # we have to use list/tuple for compatibility with py3.8


def _do_file_comparisons(args, filenames: Iterable[str], logger: CLILogger) -> FileComparisons:
    _rel_tol_map = _parse_field_tolerances(args.get("relative_tolerance"))
    _abs_tol_map = _parse_field_tolerances(args.get("absolute_tolerance"), allow_dynamic_tolerances=True)

    file_comparisons = []
    # ruff: noqa: PERF203
    for i, filename in enumerate(filenames):
        timestamp = datetime.now().isoformat()
        res_file = join(args["source-dir"], filename)
        ref_file = join(args["reference-dir"], filename)

        logger.log(("\n" if i > 0 else ""), verbosity_level=1)
        logger.log(f"Comparing '{highlighted(res_file)}'\n" f"      and '{highlighted(ref_file)}'\n", verbosity_level=1)

        opts = FileComparisonOptions(
            ignore_missing_source_fields=args["ignore_missing_source_fields"],
            ignore_missing_reference_fields=args["ignore_missing_reference_fields"],
            ignore_missing_sequence_steps=args["ignore_missing_sequence_steps"],
            relative_tolerances=_rel_tol_map,
            absolute_tolerances=_abs_tol_map,
            field_inclusion_filter=PatternFilter(args["include_fields"]) if args["include_fields"] else _include_all(),
            field_exclusion_filter=PatternFilter(args["exclude_fields"]) if args["exclude_fields"] else _exclude_all(),
            disable_mesh_reordering=True if args["disable_mesh_reordering"] else False,
            disable_mesh_space_dimension_matching=True if args["disable_mesh_space_dimension_matching"] else False,
            disable_unconnected_points_removal=True if args["disable_mesh_orphan_point_removal"] else False,
            file_type_map=_make_file_type_map(args.get("read_as", [])),
        )
        try:
            sub_logger = logger.with_prefix("  ")
            comparator = FileComparison(opts, sub_logger.with_modified_verbosity(-1), args["diff"])
            cpu_time, test_suite = _measure_time(comparator)(res_file, ref_file)
            file_comparisons.append(
                (
                    filename,
                    timestamp,
                    test_suite.with_overridden(
                        cpu_time=cpu_time,
                        name=_suite_name(res_file),
                        shortlog=_get_failing_field_test_names(test_suite),
                    ),
                )
            )

            if test_suite.num_tests == 0:
                sub_logger.log(f"File comparison {get_status_string(bool(test_suite))}\n")
            else:
                sub_logger.log(
                    "File comparison {} with {} {} / {} {} / {} {}\n".format(
                        get_status_string(bool(test_suite)),
                        sum(1 for t in test_suite if t.status == TestStatus.passed),
                        f"{TestStatus.passed}",
                        sum(1 for t in test_suite if not t.status),
                        f"{TestStatus.failed}",
                        sum(1 for t in test_suite if t.status and t.status != TestStatus.passed),
                        f"{TestStatus.skipped}",
                    ),
                    verbosity_level=1,
                )
        except Exception as e:
            output = f"Error upon file comparison: {str(e)}"
            logger.log(output, verbosity_level=1)
            file_comparisons.append(
                (
                    filename,
                    timestamp,
                    TestSuite(
                        tests=[], name=filename, status=TestStatus.error, shortlog="Exception raised", stdout=output
                    ),
                )
            )

    return file_comparisons


def _get_failing_field_test_names(test_suite: TestSuite) -> str | None:
    names = [t.name for t in test_suite if not t.status]
    if not names:
        return None

    names_string = ""
    max_num_characters = 30
    for n in names:
        quoted_name = f"'{n}'"
        if len(names_string) + len(quoted_name) > max_num_characters:
            return names_string
        names_string = quoted_name if not names_string else ";".join([names_string, quoted_name])
    return names_string


def _add_unhandled_comparisons(args: dict, categories: CategorizedFiles, comparisons: FileComparisons) -> None:
    _add_skipped_file_comparisons(
        comparisons, categories.missing_sources, "Missing source file", not args["ignore_missing_source_files"]
    )
    _add_skipped_file_comparisons(
        comparisons, categories.missing_references, "Missing reference file", not args["ignore_missing_reference_files"]
    )
    _add_skipped_file_comparisons(comparisons, categories.unsupported_files, "Unsupported file format")
    _add_skipped_file_comparisons(comparisons, categories.filtered_files, "Filtered out by given wildcard patterns")


def _add_skipped_file_comparisons(
    comparisons: FileComparisons, names: list[str], reason: str, treat_as_failure: bool = False
):
    status = TestStatus.failed if treat_as_failure else TestStatus.skipped
    for name in names:
        # insert a dummy testcase such that junit readers show a (skipped/failed) test
        suite = TestSuite(
            tests=[TestResult("file comparison", status, shortlog=reason, stdout=reason, cpu_time=None)],
            name=name,
            status=status,
            shortlog=reason,
        )
        comparisons.append((name, datetime.now().isoformat(), suite))
