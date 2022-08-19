"""Common functions used in the command-line interface"""

from typing import List, Dict, Optional, Tuple, Sequence
from re import compile
from re import error as RegexError

from .._common import _default_base_tolerance
from .._predicates import DefaultEquality, ExactEquality

from .._logging import (
    LoggerInterface,
    ModifiedVerbosityLogger,
    IndentedLogger
)

from .._field_io import (
    is_mesh_file,
    make_mesh_field_reader,
    MeshFieldReaderInterface
)

from .._mesh_fields import (
    MeshFieldContainerInterface,
    remove_ghost_points,
    sort_point_coordinates,
    sort_cells,
    sort_cell_connectivity
)

from .._field_comparison import FieldComparison
from .._file_comparison import FileComparison, FileComparisonOptions

class RegexFilter:
    """Filters lists of strings according to a list of regular expressions."""
    def __init__(self, regexes: List[str]) -> None:
        self._regexes = regexes

    def __call__(self, names: Sequence[str]) -> List[str]:
        result = []
        for regex in self._regexes:
            try:
                pattern = compile(regex)
            except RegexError as e:
                raise RuntimeError(f"Regular expression {regex} could not be compiled.\nError: {e}")
            result.extend(list(filter(lambda n: pattern.match(n), names)))
        return list(set(result))


def _include_all() -> RegexFilter:
    return RegexFilter([".*"])


def _exclude_all() -> RegexFilter:
    return RegexFilter([])


class FieldToleranceMap:
    def __init__(self,
                 default_tolerance: float = _default_base_tolerance(),
                 tolerances: Dict[str, float] = {}) -> None:
        self._default_tolerance = default_tolerance
        self._field_tolerances = tolerances

    def __call__(self, field_name: str) -> float:
        return self._field_tolerances.get(field_name, self._default_tolerance)


def _parse_field_tolerances(tolerance_strings: Optional[List[str]] = None) -> FieldToleranceMap:
    def _is_field_tolerance_string(tol_string: str) -> bool:
        return ":" in tol_string

    def _get_field_name_tolerance_value_pair(tol_string: str) -> Tuple[str, float]:
        name, tol_string = tol_string.split(":")
        return name, float(tol_string)

    if tolerance_strings is not None:
        default_tol = _default_base_tolerance()
        field_tols = {}
        for tol_string in tolerance_strings:
            if _is_field_tolerance_string(tol_string):
                name, value = _get_field_name_tolerance_value_pair(tol_string)
                field_tols[name] = value
            else:
                default_tol = float(tol_string)
        return FieldToleranceMap(default_tol, field_tols)
    return FieldToleranceMap()


def _run_file_compare(logger: LoggerInterface,
                      opts: FileComparisonOptions,
                      res_file: str,
                      ref_file: str) -> bool:
    if is_mesh_file(res_file) and is_mesh_file(ref_file):
        return _run_mesh_file_compare(logger, opts, res_file, ref_file)
    return FileComparison(opts, logger)(res_file, ref_file)


def _run_mesh_file_compare(logger: LoggerInterface,
                           opts: FileComparisonOptions,
                           result_file: str,
                           reference_file: str) -> bool:
    result_fields = _read_fields(result_file, logger)
    reference_fields = _read_fields(reference_file, logger)

    sub_logger = _get_logger_for_sorting(logger)
    reorder = not opts.disable_mesh_reordering
    if reorder and _point_coordinates_differ(result_fields, reference_fields, opts):
        logger.log(
            "Detected differences in coordinates, sorting points...\n",
            verbosity_level=1
        )

        if not opts.disable_mesh_ghost_point_removal:
            result_fields = _remove_ghost_points(result_fields, sub_logger)
            reference_fields = _remove_ghost_points(reference_fields, sub_logger)
        result_fields = _sort_points(result_fields, sub_logger)
        reference_fields = _sort_points(reference_fields, sub_logger)

    if reorder and _cell_corners_differ(result_fields, reference_fields):
        logger.log(
            "Detected differences in cell connectivity, sorting cells...\n",
            verbosity_level=1
        )
        result_fields = _sort_cells(result_fields, sub_logger)
        reference_fields = _sort_cells(reference_fields, sub_logger)

    return FieldComparison(opts, logger)(result_fields, reference_fields)


def _read_fields(filename: str, logger: LoggerInterface) -> MeshFieldContainerInterface:
    logger.log(f"Reading fields from '{filename}'\n", verbosity_level=1)
    reader = _make_mesh_field_reader(filename)
    return reader.read(filename)


def _make_mesh_field_reader(filename: str) -> MeshFieldReaderInterface:
    reader = make_mesh_field_reader(filename)
    reader.remove_ghost_points = False
    reader.permute_uniquely = False
    return reader


def _remove_ghost_points(mesh_fields: MeshFieldContainerInterface,
                         logger: LoggerInterface) -> MeshFieldContainerInterface:
    logger.log("Removing ghost points\n", verbosity_level=1)
    mesh_fields = remove_ghost_points(mesh_fields)
    return mesh_fields


def _sort_points(mesh_fields: MeshFieldContainerInterface,
                 logger: LoggerInterface) -> MeshFieldContainerInterface:
    logger.log("Sorting grid points by coordinates to get a unique representation\n", verbosity_level=1)
    mesh_fields = sort_point_coordinates(mesh_fields)
    return mesh_fields


def _sort_cells(mesh_fields: MeshFieldContainerInterface,
                logger: LoggerInterface) -> MeshFieldContainerInterface:
    logger.log("Sorting grid cells\n", verbosity_level=1)
    mesh_fields = sort_cell_connectivity(mesh_fields)
    mesh_fields = sort_cells(mesh_fields)
    return mesh_fields


def _get_logger_for_sorting(logger: LoggerInterface) -> LoggerInterface:
    low_verbosity_logger = ModifiedVerbosityLogger(logger, verbosity_change=-2)
    return IndentedLogger(low_verbosity_logger, " -- ")


def _point_coordinates_differ(fields1: MeshFieldContainerInterface,
                              fields2: MeshFieldContainerInterface,
                              opts: FileComparisonOptions) -> bool:
    field_name = "point_coordinates"
    coords1 = fields1.get(field_name).values
    coords2 = fields2.get(field_name).values
    predicate = DefaultEquality(
        abs_tol=opts.absolute_tolerances(field_name),
        rel_tol=opts.relative_tolerances(field_name)
    )
    return not bool(predicate(coords1, coords2))


def _cell_corners_differ(fields1: MeshFieldContainerInterface,
                         fields2: MeshFieldContainerInterface) -> bool:
    cell_types_1 = list(fields1.cell_types)
    cell_types_2 = list(fields2.cell_types)
    if cell_types_1.sort() != cell_types_2.sort():
        return True

    # TODO(Dennis): we should not know about how these fields are named
    def _corner_field_name(cell_type: str) -> str:
        return f"{cell_type}_corners"

    def _have_corner_fields(cell_type: str) -> bool:
        name = _corner_field_name(cell_type)
        return fields1.is_cell_corners_field(name, cell_type) \
            and fields2.is_cell_corners_field(name, cell_type)

    corner_field_names = [
        _corner_field_name(cell_type)
        for cell_type in cell_types_1 if _have_corner_fields(cell_type)
    ]
    for field_name in corner_field_names:
        corners1 = fields1.get(field_name).values
        corners2 = fields2.get(field_name).values
        if not ExactEquality()(corners1, corners2):
            return True

    return False


def _bool_to_exit_code(value: bool) -> int:
    return int(not value)
