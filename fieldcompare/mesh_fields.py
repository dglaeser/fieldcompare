"""Class to store fields defined on a mesh"""

from typing import Iterable, Tuple, List, Iterator

from ._common import _default_base_tolerance
from .array import Array, make_array, lex_sort
from .array import min_element, max_element
from .field import Field

class MeshFields:
    """Stores fields defined on a mesh. Points & cells are sorted to get a unique representation"""
    def __init__(self,
                 points: Array,
                 cells: Iterable[Tuple[str, List]]) -> None:
        points = make_array(points)
        self._point_index_map = _sorting_points_indices(points)
        self._fields: list = [
            Field("point_coordinates", points[self._point_index_map])
        ]

        point_index_map_inverse = _make_inverse_index_map(self._point_index_map)
        def _map_and_sort_cell_corners(corner_list):
            return sorted([point_index_map_inverse[c] for c in corner_list])

        self._cell_index_maps: dict = {}
        for cell_type, corners in cells:
            for idx, corner_list in enumerate(corners):
                corners[idx] = _map_and_sort_cell_corners(corner_list)
            self._cell_index_maps[cell_type] = _sorting_cell_indices(corners)
            self._fields.append(
                Field(f"{cell_type}_corners", corners[self._cell_index_maps[cell_type]])
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
        return point_data[self._point_index_map]

    def _permute_cell_data(self, cell_type: str, cell_data: Array) -> Array:
        return cell_data[self._cell_index_maps[cell_type]]


class TimeSeriesMeshFields:
    """Allows iteration over fields defined on a mesh over multiple time steps."""
    class FieldIterator:
        def __init__(self, time_series_mesh_fields) -> None:
            self._ts_mf = time_series_mesh_fields
            self._field_index = 0
            self._time_step_index = 0
            self._ts_mf._prepare_time_step_fields(self._time_step_index)

        def __next__(self):
            if self._field_index < self._num_accessible_fields():
                result = self._get_current_field()
                self._field_index += 1
                return result

            if self._has_next_time_step():
                self._ts_mf._remove_time_step_fields()
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
                 points: Array,
                 cells: Iterable[Tuple[str, List]],
                 time_series_reader) -> None:
        self._mesh_fields = MeshFields(points, cells)
        self._base_field_names = [field.name for field in self._mesh_fields]
        self._time_series_reader = time_series_reader
        self._field_iterator = None

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
        for field in self._mesh_fields:
            if field.name not in self._base_field_names:
                self._mesh_fields.remove_field(field.name)



def _sorting_points_indices(points) -> Array:
    tolerance = _get_point_cloud_tolerance(points)
    def _fuzzy_lt(val1, val2) -> bool:
        return val1 < val2 - tolerance
    def _fuzzy_gt(val1, val2) -> bool:
        return val1 > val2 + tolerance

    class _FuzzySortHelper:
        def __init__(self, idx: int) -> None:
            self._idx = idx

        def __lt__(self, other) -> bool:
            my_point = points[self._idx]
            other_point = points[other._idx]
            for v1, v2 in zip(my_point, other_point):
                if _fuzzy_lt(v1, v2):
                    return True
                elif _fuzzy_gt(v1, v2):
                    return False
            return False

    pre_sort = list(lex_sort(points))
    pre_sort.sort(key=lambda idx: _FuzzySortHelper(idx))
    return make_array(pre_sort)


def _sorting_cell_indices(cell_corner_list) -> Array:
    return lex_sort(cell_corner_list)


def _get_point_cloud_tolerance(points):
    dim = len(points[0])
    _min = [min_element(points[:, i]) for i in range(dim)]
    _max = [max_element(points[:, i]) for i in range(dim)]
    max_delta = max([_max[i] - _min[i] for i in range(dim)])
    return max_delta*_default_base_tolerance()


def _make_inverse_index_map(forward_map: Array) -> Array:
    inverse = make_array([0]*len(forward_map))
    for list_index, mapped_index in enumerate(forward_map):
        inverse[mapped_index] = list_index
    return inverse
