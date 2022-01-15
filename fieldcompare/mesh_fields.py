"""Class to store fields defined on a mesh"""

from typing import Iterable, Tuple, List

from fieldcompare._common import _default_base_tolerance
from fieldcompare.array import Array, make_array, lex_sort
from fieldcompare.field import Field

class MeshFields:
    """Stores fields defined on a mesh. Points & cells are sorted to get a unique representation"""
    def __init__(self,
                 points: Iterable,
                 cells: Iterable[Tuple[str, Iterable]]) -> None:
        points = make_array(points)
        point_index_map = _sorting_points_indices(points)
        point_index_map_inverse = _make_inverse_index_map(point_index_map)

        def _map_and_sort_cell_corners(corner_list):
            return sorted([point_index_map_inverse[c] for c in corner_list])
        cells = {
            cell_type: make_array([_map_and_sort_cell_corners(c) for c in corners])
            for cell_type, corners in cells
        }
        cell_index_maps = {
            cell_type: _sorting_cell_indices(corners)
            for cell_type, corners in cells.items()
        }

        self._point_index_map = point_index_map
        self._cell_index_maps = cell_index_maps

        self._fields: list = []
        self._fields.append(
            Field("point_coordinates", points[point_index_map])
        )
        for cell_type, corners in cells.items():
            self._fields.append(
                Field(f"{cell_type}_corners", corners[cell_index_maps[cell_type]])
            )

    def __iter__(self):
        self._iter = iter(self._fields)
        return self

    def __next__(self) -> Field:
        return next(self._iter)

    def __len__(self) -> int:
        return len(self._fields)

    def __getitem__(self, index: int):
        return self._fields[index]


def _sorting_points_indices(points) -> Array:
    class _FuzzySortHelper:
        def __init__(self, value: float, tolerance: float) -> None:
            self._value = value
            self._tolerance = tolerance

        def __eq__(self, other) -> bool:
            abs_diff = abs(self._value - other._value)
            return abs_diff <= self._tolerance

        def __lt__(self, other) -> bool:
            if not self.__eq__(other):
                return self._value < other._value
            return False

    tolerance = _get_point_cloud_tolerance(points)
    def _make_fuzzy_sortable_point(point):
        return make_array([_FuzzySortHelper(v, tolerance) for v in point])

    pre_sort = lex_sort(points)
    pre_sorted_fuzzy_comparable = make_array([
        _make_fuzzy_sortable_point(points[idx]) for idx in pre_sort
    ])
    fuzzy_sort = lex_sort(pre_sorted_fuzzy_comparable)
    return make_array([pre_sort[idx] for idx in fuzzy_sort])


def _sorting_cell_indices(cell_corner_list) -> Array:
    return lex_sort(cell_corner_list)


def _get_point_cloud_tolerance(points):
    dim = len(points[0])
    _min = [1e20]*dim
    _max = [-1e20]*dim
    for p in points:
        for i, coord in enumerate(p):
            _min[i] = min(coord, _min[i])
            _max[i] = max(coord, _max[i])
    max_delta = max([_max[i] - _min[i] for i in range(dim)])
    return max_delta*_default_base_tolerance()


def _make_inverse_index_map(forward_map: Array) -> Array:
    inverse = make_array([0]*len(forward_map))
    for list_index, mapped_index in enumerate(forward_map):
        inverse[mapped_index] = list_index
    return inverse
