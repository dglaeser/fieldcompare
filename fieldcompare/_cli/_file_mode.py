"""Command-line interface for comparing a pair of files"""

from os.path import basename
from argparse import ArgumentParser
from datetime import datetime
from xml.etree.ElementTree import ElementTree

from .._common import _measure_time

from ._junit import as_junit_xml_element
from ._logger import CLILogger
from ._file_comparison import FileComparison, FileComparisonOptions

from ._common import (
    PatternFilter,
    _bool_to_exit_code,
    _parse_field_tolerances,
    _include_all,
    _exclude_all,
    _log_suite_summary
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
        default=1,
        type=int,
        help="Set the verbosity level"
    )
    _add_field_options_args(parser)
    _add_tolerance_options_args(parser)
    _add_field_filter_options_args(parser)
    _add_mesh_reorder_options_args(parser)
    _add_junit_export_arg(parser)


def _run(args: dict, in_logger: CLILogger) -> int:
    timestamp = datetime.now().isoformat()
    logger = in_logger.with_verbosity(args["verbosity"])
    opts = FileComparisonOptions(
        ignore_missing_result_fields=args["ignore_missing_result_fields"],
        ignore_missing_reference_fields=args["ignore_missing_reference_fields"],
        ignore_missing_sequence_steps=args["ignore_missing_sequence_steps"],
        relative_tolerances=_parse_field_tolerances(args.get("relative_tolerance")),
        absolute_tolerances=_parse_field_tolerances(args.get("absolute_tolerance")),
        field_inclusion_filter=PatternFilter(args["include_fields"]) if args["include_fields"] else _include_all(),
        field_exclusion_filter=PatternFilter(args["exclude_fields"]) if args["exclude_fields"] else _exclude_all(),
        disable_mesh_reordering=True if args["disable_mesh_reordering"] else False,
        disable_unconnected_points_removal=True if args["disable_mesh_orphan_point_removal"] else False
    )

    try:
        comparator = FileComparison(opts, logger)
        cpu_time, test_suite = _measure_time(comparator)(args["file"], args["reference"])
        passed = bool(test_suite)
        logger.log("\n")
        _log_suite_summary(test_suite, "field", logger)

        if args["junit_xml"] is not None:
            ElementTree(
                as_junit_xml_element(test_suite.with_overridden(cpu_time=cpu_time), timestamp)
            ).write(
                args["junit_xml"], xml_declaration=True
            )

    except Exception as e:
        logger.log(f"Error upon file comparison: {str(e)}")
        passed = False

    return _bool_to_exit_code(passed)


def _add_mesh_reorder_options_args(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--disable-mesh-reordering",
        required=False,
        action="store_true",
        help="For fields defined on meshes, the mesh is reordered in a unique way in case differences "
             "in the point coordinates or the mesh connectivity are detected. This ensures that the "
             "comparisons pass also for rearranged meshes when the field data matches. Use this flag "
             "to disable this behaviour in case you want to test for identical mesh ordering."
    )
    parser.add_argument(
        "--disable-mesh-orphan-point-removal",
        required=False,
        action="store_true",
        help="Per default, orphan (unconnected) points are removed from the mesh before a reordering "
             "of the points is carried out, since on meshes with multiple orphan points at the same "
             "position there is no way to sort them uniquely. Use this flag to deactivate this behaviour "
             "in case you want to test the orphan points also on reordered meshes. Keep in mind that this "
             "may not work on meshes where orphan points coincide with any other points."
    )


def _add_field_filter_options_args(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--include-fields",
        required=False,
        action="append",
        help="Pass a Unix-style wildcard pattern to filter fields to be compared. This option can "
             "be used multiple times. Field names that match any of the patterns are considered. "
             "If this argument is not specified, all fields are considered."
    )
    parser.add_argument(
        "--exclude-fields",
        required=False,
        action="append",
        help="Pass a Unix-style wildcard pattern to exclude fields from the comparisons. This option can "
             "be used multiple times. Field names that match any of the patterns are excluded. "
    )


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
    parser.add_argument(
        "--ignore-missing-sequence-steps",
        required=False,
        action="store_true",
        help="Treat missing sequence steps as warning and compare only the common steps"
    )


def _add_tolerance_options_args(parser: ArgumentParser) -> None:
    parser.add_argument(
        "-rtol", "--relative-tolerance",
        required=False,
        nargs="*",
        help="Specify the relative tolerance to be used. "
             "Use e.g. '-rtol pressure:1e-3' to set the tolerance for a field named 'pressure'"
    )
    parser.add_argument(
        "-atol", "--absolute-tolerance",
        required=False,
        nargs="*",
        help="Specify the absolute tolerance to be used. "
             "Use e.g. '-atol pressure:1e-3' to set the tolerance for a field named 'pressure'"
    )


def _add_junit_export_arg(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--junit-xml",
        required=False,
        help="Pass the filename into which a junit report should be written"
    )
