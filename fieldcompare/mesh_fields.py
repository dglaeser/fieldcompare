"""Class to store fields defined on a mesh"""

from typing import Iterable, Tuple, Iterator, Dict

from ._common import _default_base_tolerance
from .array import Array, is_array, make_array, make_uninitialized_array, append_to_array
from .array import adjacent_difference, elements_less, accumulate
from .array import sort_array, lex_sort_array_columns
from .array import min_element, max_element, abs_array, all_true
from .field import Field
from .logging import Logger, NullDeviceLogger


MeshPoints = Array
CellCorners = Array
MeshCells = Iterable[Tuple[str, CellCorners]]
Mesh = Tuple[MeshPoints, MeshCells]


class MeshFields:
    """
        Represents fields defined on a mesh.
        Allows sorting of points & cells to get a unique
        representation of a mesh independent of the order.
    """
    def __init__(self,
                 mesh: Mesh,
                 do_sorting: bool = True,
                 logger: Logger = NullDeviceLogger()) -> None:
        self._do_sorting = do_sorting
        self._point_index_map = make_array([])
        self._cell_index_maps: dict = {}

        points = _get_mesh_points(mesh)
        cells = _get_mesh_cells_dict(mesh)

        if do_sorting:
            self._point_index_map = _sorting_points_indices(points, cells, logger)
            point_index_map_inverse = _make_inverse_index_map(self._point_index_map)
        self._fields: list = [
            Field(
                "point_coordinates",
                points[self._point_index_map] if do_sorting else points
            )
        ]

        def _map_and_sort_cell_corners(corner_list):
            return sort_array(point_index_map_inverse[corner_list])

        for cell_type, corners in cells.items():
            for idx, corner_list in enumerate(corners):
                corners[idx] = _map_and_sort_cell_corners(corner_list)
            if do_sorting:
                self._cell_index_maps[cell_type] = _sorting_cell_indices(corners, cell_type, logger)
            self._fields.append(
                Field(
                    f"{cell_type}_corners",
                    corners[self._cell_index_maps[cell_type]] if do_sorting else corners
                )
            )

    def add_point_data(self, name: str, values: Array) -> None:
        """Add point data values. Expects the ordering to follow the points given to __init__."""
        values = make_array(values)
        self._fields.append(Field(name, self._permute_point_data(values)))

    def add_cell_data(self, name: str, values: Iterable[Tuple[str, Array]]) -> None:
        """Add cell data values. Expects an iterable over (cell_type, cell_values)."""
        for cell_type, cell_type_values in values:
            cell_type_values = make_array(cell_type_values)
            self._fields.append(Field(
                f"{cell_type}_{name}",
                self._permute_cell_data(cell_type, cell_type_values)
            ))

    def remove_field(self, name: str) -> bool:
        """Remove the field with the given name"""
        for field in self._fields:
            if field.name == name:
                self._fields.remove(field)
                return True
        raise ValueError(f"No field with name {name}")

    def __iter__(self) -> Iterator[Field]:
        return iter(self._fields)

    def __len__(self) -> int:
        return len(self._fields)

    def __getitem__(self, index: int):
        return self._fields[index]

    def _permute_point_data(self, point_data: Array) -> Array:
        if self._do_sorting:
            return point_data[self._point_index_map]
        return point_data

    def _permute_cell_data(self, cell_type: str, cell_data: Array) -> Array:
        if self._do_sorting:
            return cell_data[self._cell_index_maps[cell_type]]
        return cell_data


class TimeSeriesMeshFields:
    """Allows iteration over fields defined on a mesh over multiple time steps."""
    class FieldIterator:
        def __init__(self, time_series_mesh_fields) -> None:
            self._ts_mf = time_series_mesh_fields
            self._field_index = 0
            self._time_step_index = 0
            self._ts_mf._remove_time_step_fields()
            self._ts_mf._prepare_time_step_fields(self._time_step_index)

        def __next__(self):
            if self._field_index < self._num_accessible_fields():
                result = self._get_current_field()
                self._field_index += 1
                return result

            self._ts_mf._remove_time_step_fields()
            if self._has_next_time_step():
                self._time_step_index += 1
                self._ts_mf._prepare_time_step_fields(self._time_step_index)
                self._field_index = self._ts_mf._get_index_after_base_fields()
                result = self._get_current_field()
                self._field_index += 1
                return result
            raise StopIteration

        def _get_current_field(self) -> Field:
            return self._ts_mf._mesh_fields[self._field_index]

        def _num_accessible_fields(self) -> int:
            return len(self._ts_mf._mesh_fields)

        def _has_next_time_step(self) -> bool:
            return self._time_step_index + 1 < self._ts_mf._time_series_reader.num_time_steps

    def __init__(self,
                 mesh: Mesh,
                 time_series_reader,
                 sort_by_coordinates: bool = True,
                 logger: Logger = NullDeviceLogger()) -> None:
        self._mesh_fields = MeshFields(mesh, sort_by_coordinates, logger)
        self._base_field_names = [field.name for field in self._mesh_fields]
        self._time_series_reader = time_series_reader
        self._field_iterator = self.FieldIterator(self)

    def __iter__(self):
        self._field_iterator = self.FieldIterator(self)
        return self

    def __next__(self):
        return next(self._field_iterator)

    def _get_index_after_base_fields(self) -> int:
        return len(self._base_field_names)

    def _prepare_time_step_fields(self, time_step_index: int) -> None:
        point_data, cell_data = self._time_series_reader.read_time_step(time_step_index)

        def _add_suffix(array_name) -> str:
            return f"{array_name}_timestep_{time_step_index}"

        for array_name, values in point_data:
            self._mesh_fields.add_point_data(
                _add_suffix(array_name), values
            )
        for array_name, cell_type_values_tuple_range in cell_data:
            self._mesh_fields.add_cell_data(
                _add_suffix(array_name),
                cell_type_values_tuple_range
            )

    def _remove_time_step_fields(self) -> None:
        fields_to_remove = filter(
            lambda n: n not in self._base_field_names,
            [f.name for f in self._mesh_fields]
        )
        for field_name in fields_to_remove:
            self._mesh_fields.remove_field(field_name)


def _get_mesh_points(mesh: Mesh) -> Array:
    mesh_points, _ = mesh
    if is_array(mesh_points):
        return mesh_points
    return make_array(mesh_points)


def _get_mesh_cells_dict(mesh: Mesh) -> Dict[str, CellCorners]:
    _, mesh_cells = mesh
    return {cell_type: corners for cell_type, corners in mesh_cells}


def _sorting_points_indices(points, cells, logger: Logger = NullDeviceLogger()) -> Array:
    logger.log("Sorting point coordinates lexicographically\n", verbosity_level=1)
    tolerance = _get_point_cloud_tolerance(points)
    def _fuzzy_lt(val1, val2) -> bool:
        return val1 < val2 - tolerance
    def _fuzzy_gt(val1, val2) -> bool:
        return val1 > val2 + tolerance
    def _fuzzy_lt_point(p1, p2) -> bool:
        for v1, v2 in zip(p1, p2):
            if _fuzzy_lt(v1, v2):
                return True
            elif _fuzzy_gt(v1, v2):
                return False
        return False

    class _IndexedFuzzySortHelper:
        def __init__(self, idx: int) -> None:
            self._idx = idx
        def __lt__(self, other) -> bool:
            return _fuzzy_lt_point(
                points[self._idx],
                points[other._idx]
            )

    pre_sort = list(lex_sort_array_columns(points))
    pre_sort.sort(key=lambda idx: _IndexedFuzzySortHelper(idx))

    # for non-conforming output, there may be multiple points at the same position
    # sort those according to the minimum cell center they are connected to
    def _make_empty_point_connectivity_list() -> Array:
        arr = make_uninitialized_array(len(points), dtype=list)
        for idx in range(len(arr)):
            arr[idx] = []
        return arr

    cells_around_points = {
        cell_type: _make_empty_point_connectivity_list()
        for cell_type, _ in cells.items()
    }
    for cell_type, corners in cells.items():
        for idx, cell_corners in enumerate(corners):
            for point_index in cell_corners:
                cells_around_points[cell_type][point_index].append(idx)

    class _FuzzyPointSortHelper:
        def __init__(self, point):
            self._point = point
        def __lt__(self, other) -> bool:
            return _fuzzy_lt_point(self._point, other._point)

    def _compute_cell_center(cell_corner_list):
        return accumulate(points[cell_corner_list], axis=0)/len(cell_corner_list)

    def _compute_min_cell_center_around_point(point_idx):
        def _compute_current_cell_center(cell_type, cell_idx):
            for ct, corners in cells.items():
                if ct == cell_type:
                    return _compute_cell_center(corners[cell_idx])
            raise ValueError("Could not find")

        centers = []
        for cell_type in cells_around_points:
            if cells_around_points[cell_type][point_idx] is not None:
                for cell_index in cells_around_points[cell_type][point_idx]:
                    centers.append(_FuzzyPointSortHelper(
                        _compute_current_cell_center(cell_type, cell_index)
                    ))
        return min(centers)

    diffs = adjacent_difference(points[pre_sort], axis=0)
    diffs = abs_array(diffs)
    is_zero_diff = make_array(diffs)
    is_zero_diff.fill(tolerance)
    is_zero_diff = elements_less(diffs, is_zero_diff)
    is_zero_diff = all_true(is_zero_diff, axis=1)
    is_zero_diff = append_to_array(is_zero_diff, False)

    equal_orig_point_indices = []
    if any(is_zero_diff):
        logger.log("Uniquely sorting identical coordinates\n", verbosity_level=2)
    for list_idx, is_zero in enumerate(is_zero_diff):
        if is_zero:
            equal_orig_point_indices.append(list_idx)
        elif equal_orig_point_indices:
            # sort chunk of equal points
            equal_orig_point_indices.append(list_idx)
            start = equal_orig_point_indices[0]
            stop = equal_orig_point_indices[-1]

            min_cell_centers = {
                orig_pidx: _compute_min_cell_center_around_point(pre_sort[orig_pidx])
                for orig_pidx in equal_orig_point_indices
            }
            equal_orig_point_indices.sort(key=lambda orig_pidx: min_cell_centers[orig_pidx])
            pre_sort[start:stop+1] = [pre_sort[orig_idx] for orig_idx in equal_orig_point_indices]
            equal_orig_point_indices = []
    return make_array(pre_sort)


def _sorting_cell_indices(cell_corner_list, cell_type: str, logger: Logger) -> Array:
    logger.log(f"Sorting cells of type '{cell_type}'\n", verbosity_level=1)
    return lex_sort_array_columns(cell_corner_list)


def _get_point_cloud_tolerance(points):
    dim = len(points[0])
    _min = [min_element(points[:, i]) for i in range(dim)]
    _max = [max_element(points[:, i]) for i in range(dim)]
    max_delta = max([_max[i] - _min[i] for i in range(dim)])
    return max_delta*_default_base_tolerance()


def _make_inverse_index_map(forward_map: Array) -> Array:
    inverse = make_array(forward_map)
    for list_index, mapped_index in enumerate(forward_map):
        inverse[mapped_index] = list_index
    return inverse
