"""Command-line interface for comparing a pair of files"""

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
    _log_suite_summary,
    _make_file_type_map,
)


def _add_arguments(parser: ArgumentParser):
    parser.add_argument("source", type=str, help="The file which is to be compared against a reference file")
    parser.add_argument("reference", type=str, help="The reference file against which to compare")
    parser.add_argument("--verbosity", required=False, default=2, type=int, help="Set the verbosity level")
    _add_field_options_args(parser)
    _add_tolerance_options_args(parser)
    _add_field_filter_options_args(parser)
    _add_mesh_reorder_options_args(parser)
    _add_junit_export_arg(parser)
    _add_reader_selection_options_args(parser)


def _run(args: dict, in_logger: CLILogger) -> int:
    timestamp = datetime.now().isoformat()
    logger = in_logger.with_verbosity(args["verbosity"])
    opts = FileComparisonOptions(
        ignore_missing_source_fields=args["ignore_missing_source_fields"],
        ignore_missing_reference_fields=args["ignore_missing_reference_fields"],
        ignore_missing_sequence_steps=args["ignore_missing_sequence_steps"],
        force_sequence_comparison=args["force_sequence_comparison"],
        relative_tolerances=_parse_field_tolerances(args.get("relative_tolerance")),
        absolute_tolerances=_parse_field_tolerances(args.get("absolute_tolerance"), allow_dynamic_tolerances=True),
        field_inclusion_filter=PatternFilter(args["include_fields"]) if args["include_fields"] else _include_all(),
        field_exclusion_filter=PatternFilter(args["exclude_fields"]) if args["exclude_fields"] else _exclude_all(),
        disable_mesh_reordering=True if args["disable_mesh_reordering"] else False,
        disable_mesh_space_dimension_matching=True if args["disable_mesh_space_dimension_matching"] else False,
        disable_unconnected_points_removal=True if args["disable_mesh_orphan_point_removal"] else False,
        file_type_map=_make_file_type_map(args.get("read_as", [])),
    )

    try:
        comparator = FileComparison(opts, logger)
        cpu_time, test_suite = _measure_time(comparator)(args["source"], args["reference"])
        passed = bool(test_suite)
        logger.log("\n")
        _log_suite_summary(test_suite, "field", logger)

        if args["junit_xml"] is not None:
            ElementTree(as_junit_xml_element(test_suite.with_overridden(cpu_time=cpu_time), timestamp)).write(
                args["junit_xml"], xml_declaration=True
            )

    except Exception as e:
        logger.log(f"Error upon file comparison: {str(e)}\n")
        passed = False

    return _bool_to_exit_code(passed)


def _add_mesh_reorder_options_args(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--disable-mesh-reordering",
        required=False,
        action="store_true",
        help="For fields defined on meshes, the mesh is reordered in a unique way in case differences "
        "in the point coordinates or the mesh connectivity are detected. This ensures that the "
        "comparisons pass also for meshes that are differently ordered when the field data matches. "
        "Use this flag to disable this behaviour in case you want to test for identical mesh ordering.",
    )
    parser.add_argument(
        "--disable-mesh-orphan-point-removal",
        required=False,
        action="store_true",
        help="Per default, orphan (unconnected) points are removed from the mesh before a reordering "
        "of the points is carried out, since on meshes with multiple orphan points at the same "
        "position there is no way to sort them uniquely. Use this flag to deactivate this behaviour "
        "in case you want to test the orphan points also on reordered meshes. Keep in mind that this "
        "may not work on meshes where orphan points coincide with any other points.",
    )
    parser.add_argument(
        "--disable-mesh-space-dimension-matching",
        required=False,
        action="store_true",
        help="Per default, the space dimension of meshes and associated vector/tensor fields is matched by "
        "filling up the fields with zeros. Use this flag to deactivate this behaviour.",
    )


def _add_field_filter_options_args(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--include-fields",
        required=False,
        action="append",
        help="Pass a Unix-style wildcard pattern to filter fields to be compared. This option can "
        "be used multiple times. Field names that match any of the patterns are considered. "
        "If this argument is not specified, all fields are considered.",
    )
    parser.add_argument(
        "--exclude-fields",
        required=False,
        action="append",
        help="Pass a Unix-style wildcard pattern to exclude fields from the comparisons. This option can "
        "be used multiple times. Field names that match any of the patterns are excluded. ",
    )


def _add_field_options_args(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--ignore-missing-source-fields",
        required=False,
        action="store_true",
        help="Use this flag to treat missing source fields as warnings only",
    )
    parser.add_argument(
        "--ignore-missing-reference-fields",
        required=False,
        action="store_true",
        help="Use this flag to treat missing reference fields as warnings only",
    )
    parser.add_argument(
        "--ignore-missing-sequence-steps",
        required=False,
        action="store_true",
        help="Treat missing sequence steps as warning and compare only the common steps",
    )
    parser.add_argument(
        "--force-sequence-comparison",
        required=False,
        action="store_true",
        help="This flag forces the comparison of common steps in two sequences although the "
        "sequences have different lengths. The comparison is considered failed because "
        "of the different sequences lengths, but the output of the comparison of common "
        "steps is produced. To treat differing lengths as warnings, see 'ignore-missing-sequence-steps",
    )


def _add_tolerance_options_args(parser: ArgumentParser) -> None:
    parser.add_argument(
        "-rtol",
        "--relative-tolerance",
        required=False,
        nargs="*",
        help="Specify the relative tolerance to be used. "
        "Use e.g. '-rtol pressure:1e-3' to set the tolerance for a field named 'pressure', "
        "or '-rtol domain:1e-3' to define the tolerance used when checking the domains for equality.",
    )
    parser.add_argument(
        "-atol",
        "--absolute-tolerance",
        required=False,
        nargs="*",
        help="Specify the absolute tolerance to be used. "
        "Use e.g. '-atol pressure:1e-3' to set the tolerance for a field named 'pressure' "
        "or '-atol domain:1e-3' to define the tolerance used when checking the domains for equality. "
        "You may also use absolute tolerances as a function of the maximum absolute value occurring "
        "in the fields by using the syntax: `-atol pressure:1e-3*max`. This is useful for fields with "
        "a large range where all values are expected to exhibit similar absolute errors. This option "
        "then avoids false negatives from values close to zero.",
    )


def _add_reader_selection_options_args(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--read-as",
        nargs="*",
        required=False,
        help="Specify the reader to be used for parsing the fields from files (per default, the reader is deduced "
        "from the file extension). To specify that a file should be read by the mesh reading facilities, for instance, "
        "use the following syntax: `--read-as mesh:MY_FILE`. In general, the syntax is `READER:REGEX`, where `READER` "
        "specifies the reading facilities to be used, and `REGEX` is a regular expression that is evaluated with "
        "filenames to check if `READER` should be used for them. For instance, to read `.dat` with delimiter-separated "
        "content with the `dsv` facilities, use `--read-as dsv:*.dat`. This option can be used multiple times, and "
        "in case a filename matches multiple of the given regular expressions, the first match is taken. For example, "
        "`--read-as dsv:*.dat --read-as mesh:*.dat` leads to `.dat` files being read as `dsv`.",
    )


def _add_junit_export_arg(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--junit-xml", required=False, help="Pass the filename into which a junit report should be written"
    )
