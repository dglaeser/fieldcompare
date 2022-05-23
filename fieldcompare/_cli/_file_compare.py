"""Command-line interface for comparing a pair of files"""

from argparse import ArgumentParser

from .._logging import LoggerInterface
from .._file_comparison import FileComparisonOptions
from .._format import get_status_string

from ._common import (
    _bool_to_exit_code,
    _parse_field_tolerances,
    _run_file_compare,
    RegexFilter
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
        help="Pass a regular expression used to filter fields to be compared. This option can "
             "be used multiple times. Field names that match any of the patterns are considered. "
             "If this argument is not specified, all fields are considered."
    )
    parser.add_argument(
        "--exclude-fields",
        required=False,
        action="append",
        help="Pass a regular expression used to exclude fields from the comparisons. This option can "
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
             "Use e.g. '-rtol 1e-3:pressure' to set the tolerance for a field named 'pressure'"
    )
    parser.add_argument(
        "-atol", "--absolute-tolerance",
        required=False,
        nargs="*",
        help="Specify the absolute tolerance to be used. "
             "Use e.g. '-atol 1e-3:pressure' to set the tolerance for a field named 'pressure'"
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
        default=2,
        type=int,
        help="Set the verbosity level"
    )
    _add_field_options_args(parser)
    _add_tolerance_options_args(parser)
    _add_field_filter_options_args(parser)
    _add_mesh_reorder_options_args(parser)


def _run(args: dict, logger: LoggerInterface) -> int:
    logger.verbosity_level = args["verbosity"]
    opts = FileComparisonOptions(
        ignore_missing_result_fields=args["ignore_missing_result_fields"],
        ignore_missing_reference_fields=args["ignore_missing_reference_fields"],
        relative_tolerances=_parse_field_tolerances(args.get("relative_tolerance")),
        absolute_tolerances=_parse_field_tolerances(args.get("absolute_tolerance")),
        field_inclusion_filter=RegexFilter(args["include_fields"] if args["include_fields"] else ["*"]),
        field_exclusion_filter=RegexFilter(args["exclude_fields"]),
        disable_mesh_reordering=True if args["disable_mesh_reordering"] else False,
        disable_mesh_ghost_point_removal=True if args["disable_mesh_ghost_point_removal"] else False
    )

    try:
        passed = _run_file_compare(logger, opts, args["file"], args["reference"])
    except Exception as e:
        logger.log(str(e), verbosity_level=1)
        passed = False

    logger.log("File comparison {}\n".format(get_status_string(passed)))
    return _bool_to_exit_code(passed)
