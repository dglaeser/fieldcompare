"""Command-line interface for comparing a pair of files"""

from os.path import basename
from argparse import ArgumentParser
from datetime import datetime
from xml.etree.ElementTree import ElementTree

from .._logging import LoggerInterface
from .._file_comparison import FileComparisonOptions
from .._format import get_status_string
from .._common import _measure_time
from .._comparison import Status

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
        "--disable-mesh-ghost-point-removal",
        required=False,
        action="store_true",
        help="Per default, ghost points are removed from the mesh before a reordering of the points "
             "is carried out, since on meshes with multiple ghost points at the same position there "
             "is no way to sort them uniquely. Use this flag to deactivate this behaviour in case "
             "you want to test the ghost points also on reordered meshes. Keep in mind that this "
             "only works on meshes where the ghost points do not coincide with any other points."
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


def _run(args: dict, logger: LoggerInterface) -> int:
    timestamp = datetime.now().isoformat()
    logger.verbosity_level = args["verbosity"]
    opts = FileComparisonOptions(
        ignore_missing_result_fields=args["ignore_missing_result_fields"],
        ignore_missing_reference_fields=args["ignore_missing_reference_fields"],
        relative_tolerances=_parse_field_tolerances(args.get("relative_tolerance")),
        absolute_tolerances=_parse_field_tolerances(args.get("absolute_tolerance")),
        field_inclusion_filter=PatternFilter(args["include_fields"]) if args["include_fields"] else _include_all(),
        field_exclusion_filter=PatternFilter(args["exclude_fields"]) if args["exclude_fields"] else _exclude_all(),
        disable_mesh_reordering=True if args["disable_mesh_reordering"] else False,
        disable_mesh_ghost_point_removal=True if args["disable_mesh_ghost_point_removal"] else False
    )

    try:
        cpu_time, comparisons = _measure_time(_run_file_compare)(logger, opts, args["file"], args["reference"])
        passed = bool(comparisons)
        logger.log("\n")
        _log_summary(
            logger,
            [comp.name for comp in comparisons if comp.status == Status.passed],
            [comp.name for comp in comparisons if not comp],
            [comp.name for comp in comparisons if comp.status == Status.skipped],
            "field",
            verbosity_level=1
        )

        if args["junit_xml"] is not None:
            suite = TestSuite(basename(args["file"]), comparisons, timestamp, cpu_time)
            ElementTree(suite.as_xml()).write(args["junit_xml"], xml_declaration=True)

    except Exception as e:
        logger.log(str(e), verbosity_level=1)
        passed = False

    logger.log("\nFile comparison {}\n".format(get_status_string(passed)))
    return _bool_to_exit_code(passed)
