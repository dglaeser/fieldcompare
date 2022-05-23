"""Mappings for mesh field containers"""

from typing import Dict, Iterable, Iterator

from .._common import _default_base_tolerance
from .._field import Field, FieldInterface
from .._array import (
    Array,
    sub_array,
    make_array,
    make_initialized_array,
    append_to_array,
    get_sorting_index_map,
    get_lex_sorting_index_map,
    accumulate,
    flatten,
    any_true,
    all_true,
    abs_array,
    min_element,
    max_element,
    elements_less,
    adjacent_difference
)

from ._mesh_fields import MeshFieldContainerInterface
from ._mesh_fields_mapped import MappedMeshFieldContainer


class _Map:
    def __init__(self, idx_map: Array) -> None:
        self._idx_map = idx_map

    def map(self, data: Array) -> Array:
        return data[self._idx_map]

    def as_indices(self) -> Array:
        return self._idx_map


def remove_ghost_points(mesh_fields: MeshFieldContainerInterface) -> MappedMeshFieldContainer:
    """Return mesh fields with ghost points removed"""
    is_ghost = make_initialized_array(
        size=len(mesh_fields.points),
        dtype=bool,
        init_value=True
    )
    for cell_type in mesh_fields.cell_types:
        for point_index in flatten(mesh_fields.connectivity(cell_type)):
            is_ghost[point_index] = False

    num_ghosts = accumulate(is_ghost)
    first_ghost_index_after_sort = int(len(is_ghost) - num_ghosts)
    ghost_filter_map = get_sorting_index_map(is_ghost)
    ghost_filter_map = sub_array(ghost_filter_map, 0, first_ghost_index_after_sort)

    return MappedMeshFieldContainer(
        mesh_fields,
        point_map=_Map(ghost_filter_map)
    )


def sort_point_coordinates(mesh_fields: MeshFieldContainerInterface) -> MappedMeshFieldContainer:
    """Return mesh fields sorted by the point coordinates"""
    try:
        point_map = _Map(_sorting_points_indices(
            mesh_fields.points,
            {ct: mesh_fields.connectivity(ct) for ct in mesh_fields.cell_types}
        ))
        return MappedMeshFieldContainer(mesh_fields, point_map=point_map)
    except ValueError as e:
        raise ValueError(
            "Could not sort the point coordinates. A known issue is that the sorting algorithm\n"
            "breaks on nonconforming meshes with ghost points. In this case, make sure\n"
            "to first strip the grids of ghost points. Caught exception:\n{}".format(e)
        )


def sort_cells(mesh_fields: MeshFieldContainerInterface) -> MappedMeshFieldContainer:
    """Return mesh fields with sorted cells"""
    return MappedMeshFieldContainer(
        mesh_fields,
        cell_maps={
            ct: _Map(_sorting_cell_indices(mesh_fields.connectivity(ct)))
            for ct in mesh_fields.cell_types
        }
    )


def sort_cell_connectivity(mesh_fields: MeshFieldContainerInterface) -> MeshFieldContainerInterface:
    """Return mesh fields where the cell corners are sorted"""
    class _SortedCornersMeshFields:
        def __init__(self,
                     mesh_fields: MeshFieldContainerInterface,
                     corner_sorting_maps: Dict[str, Array]) -> None:
            self._mesh_fields = mesh_fields
            self._corner_maps = corner_sorting_maps

        @property
        def cell_types(self) -> Iterable[str]:
            return self._mesh_fields.cell_types

        @property
        def points(self) -> Array:
            return self._mesh_fields.points

        def connectivity(self, cell_type: str) -> Array:
            return make_array([
                corners[corner_map]
                for corners, corner_map in zip(
                    self._mesh_fields.connectivity(cell_type),
                    self._corner_maps[cell_type]
                )
            ])

        # Interfaces required to be a "MeshFieldContainerInterface"
        def point_data_fields(self) -> Iterable[str]:
            return self._mesh_fields.point_data_fields()

        def cell_data_fields(self, cell_type: str) -> Iterable[str]:
            return self._mesh_fields.cell_data_fields(cell_type)

        def is_point_coordinates_field(self, field_name: str) -> bool:
            return self._mesh_fields.is_point_coordinates_field(field_name)

        def is_cell_corners_field(self, field_name: str, cell_type: str) -> bool:
            return self._mesh_fields.is_cell_corners_field(field_name, cell_type)

        # Interfaces required to be a "FieldContainerInterface"
        @property
        def field_names(self) -> Iterable[str]:
            return self._mesh_fields.field_names

        def get(self, field_name: str) -> FieldInterface:
            for cell_type in self.cell_types:
                if self.is_cell_corners_field(field_name, cell_type):
                    return Field(
                        field_name,
                        self.connectivity(cell_type)
                    )
            return self._mesh_fields.get(field_name)

        def __iter__(self) -> Iterator[FieldInterface]:
            return iter((self.get(field_name) for field_name in self.field_names))

    return _SortedCornersMeshFields(
        mesh_fields,
        corner_sorting_maps={
            ct: get_sorting_index_map(mesh_fields.connectivity(ct))
            for ct in mesh_fields.cell_types
        }
    )


def _sorting_points_indices(points, cells) -> Array:
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

    # let numpy do a quick pre sorting without fuzziness
    idx_map = list(get_lex_sorting_index_map(points))
    # now sort the pre-sorted array including fuzziness
    idx_map.sort(key=lambda idx: _IndexedFuzzySortHelper(idx))

    # find fuzzy equal neighboring points (may happen for non-conforming meshes)
    adj_diffs = _get_absolute_adjacent_diffs(points[idx_map])
    zero_diffs = _get_indices_with_zero_adjacent_diffs(adj_diffs, tolerance)

    if any_true(zero_diffs):
        # sort the chunks of equal points by sorting them according
        # to the "minimum" position of the cell centers around it
        point_to_cells_map = _get_points_to_cell_indices_map(cells, len(points))

        class _FuzzyPointSortHelper:
            def __init__(self, point):
                self._point = point
            def __lt__(self, other) -> bool:
                return _fuzzy_lt_point(self._point, other._point)

        def _compute_cell_center(cell_type: str, cell_index: int):
            cell_corner_list = cells[cell_type][cell_index]
            return accumulate(points[cell_corner_list], axis=0)/len(cell_corner_list)

        def _get_min_cell_center_around_point(point_idx):
            return min([
                _FuzzyPointSortHelper(_compute_cell_center(cell_type, cell_index))
                for cell_type in cells
                for cell_index in point_to_cells_map[cell_type][point_idx]
            ])

        equal_chunk_start_index = None
        for list_idx, is_zero in enumerate(zero_diffs):
            if is_zero:
                if equal_chunk_start_index is None:
                    equal_chunk_start_index = list_idx
            elif equal_chunk_start_index is not None:
                start = equal_chunk_start_index
                stop = list_idx + 1
                equal_point_indices = list(range(start, stop))
                equal_point_indices.sort(
                    key=lambda _idx: _get_min_cell_center_around_point(idx_map[_idx])
                )
                idx_map[start:stop] = [idx_map[_idx] for _idx in equal_point_indices]
                equal_chunk_start_index = None
    return make_array(idx_map)


def _sorting_cell_indices(cell_corner_list) -> Array:
    return get_lex_sorting_index_map(cell_corner_list)


def _get_point_cloud_tolerance(points):
    dim = len(points[0])
    _min = [min_element(points[:, i]) for i in range(dim)]
    _max = [max_element(points[:, i]) for i in range(dim)]
    max_delta = max([_max[i] - _min[i] for i in range(dim)])
    return max_delta*_default_base_tolerance()


def _get_absolute_adjacent_diffs(points: Array) -> Array:
    diffs = adjacent_difference(points, axis=0)
    return abs_array(diffs)


def _get_indices_with_zero_adjacent_diffs(adjacent_diffs: Array, tolerance: float) -> Array:
    is_zero_diff = make_array(adjacent_diffs)
    is_zero_diff.fill(tolerance)
    is_zero_diff = elements_less(adjacent_diffs, is_zero_diff)
    is_zero_diff = all_true(is_zero_diff, axis=1)
    is_zero_diff = append_to_array(is_zero_diff, False)
    return is_zero_diff


def _get_points_to_cell_indices_map(cells, num_points) -> Dict[str, list]:
    def _get_cells_around_points(_cells) -> list:
        result: list = [[] for _ in range(num_points)]
        for cell_idx, _corners in enumerate(_cells):
            for _corner_idx in _corners:
                result[_corner_idx].append(cell_idx)
        return result

    return {
        cell_type: _get_cells_around_points(corners)
        for cell_type, corners in cells.items()
    }
