"""Data structure to represent meshes"""

from typing import Dict, Protocol

from .._common import _default_base_tolerance
from ..array import (
    Array,
    sort_array, lex_sort_array_columns,
    make_array, make_initialized_array, make_uninitialized_array, append_to_array,
    sub_array, flatten,
    accumulate,
    adjacent_difference,
    abs_array,
    elements_less,
    all_true,
    min_element,
    max_element
)

MeshConnectivity = Dict[str, Array]

class MeshInterface(Protocol):
    @property
    def points(self) -> Array:
        ...

    @property
    def connectivity(self) -> MeshConnectivity:
        ...


class TransformedMeshInterface(MeshInterface, Protocol):
    def mesh(self) -> MeshInterface:
        ...

    def transform_point_data(self, data: Array) -> Array:
        ...

    def transform_cell_data(self, cell_type: str, data: Array) -> Array:
        ...


class Mesh:
    def __init__(self,
                 points: Array,
                 connectivity: MeshConnectivity) -> None:
        self._points = points
        self._connectivity = connectivity

    @property
    def points(self) -> Array:
        return self._points

    @property
    def connectivity(self) -> MeshConnectivity:
        return self._connectivity


class TransformedMeshBase:
    def __init__(self,
                 points: Array,
                 connectivity: MeshConnectivity) -> None:
        self._points = points
        self._connectivity = connectivity

    @property
    def points(self) -> Array:
        return self._points

    @property
    def connectivity(self) -> MeshConnectivity:
        return self._connectivity

    def mesh(self) -> Mesh:
        return Mesh(self.points, self.connectivity)


def transform_identity(mesh: MeshInterface) -> TransformedMeshInterface:
    """Return a transformed mesh with identity transformation"""
    class IdentityTransformedMesh(TransformedMeshBase):
        def __init__(self,
                     points: Array,
                     connectivity: MeshConnectivity) -> None:
            super().__init__(points, connectivity)

        def transform_point_data(self, data: Array) -> Array:
            return data

        def transform_cell_data(self, cell_type: str, data: Array) -> Array:
            return data
    return IdentityTransformedMesh(mesh.points, mesh.connectivity)


def transform_without_ghosts(mesh: MeshInterface) -> TransformedMeshInterface:
    """Return a transformed mesh where ghost points are removed"""
    class GhostsRemovedTransformedMesh(TransformedMeshBase):
        def __init__(self,
                     points: Array,
                     connectivity: MeshConnectivity,
                     point_index_map: Array) -> None:
            super().__init__(points, connectivity)
            self._point_index_map = point_index_map

        def transform_point_data(self, data: Array) -> Array:
            return data[self._point_index_map]

        def transform_cell_data(self, cell_type: str, data: Array) -> Array:
            return data

    is_ghost = make_initialized_array(size=len(mesh.points), dtype=bool, init_value=True)
    for _, corners in mesh.connectivity.items():
        for p_idx in flatten(corners):
            is_ghost[p_idx] = False

    num_ghosts = accumulate(is_ghost)
    first_ghost_index_after_sort = int(len(is_ghost) - num_ghosts)

    ghost_filter_map = sort_array(is_ghost)
    ghost_filter_map = sub_array(ghost_filter_map, 0, first_ghost_index_after_sort)
    ghost_filter_map_inverse = _make_inverse_index_map(ghost_filter_map)
    new_connectivity = {
        cell_type: make_array([
            ghost_filter_map_inverse[_cell_corners] for _cell_corners in corners
        ])
        for cell_type, corners in mesh.connectivity.items()
    }

    return GhostsRemovedTransformedMesh(
        points=mesh.points[ghost_filter_map],
        connectivity=new_connectivity,
        point_index_map=ghost_filter_map
    )


def transform_sorted(mesh: MeshInterface) -> TransformedMeshInterface:
    """Return a transformed mesh that is sorted by the point coordinates"""
    class SortedMesh(TransformedMeshBase):
        def __init__(self,
                     points: Array,
                     connectivity: MeshConnectivity,
                     point_index_map: Array,
                     cell_index_maps: Dict[str, Array]) -> None:
            super().__init__(points, connectivity)
            self._point_index_map = point_index_map
            self._cell_index_maps = cell_index_maps

        def transform_point_data(self, data: Array) -> Array:
            return data[self._point_index_map]

        def transform_cell_data(self, cell_type: str, data: Array) -> Array:
            return data[self._cell_index_maps[cell_type]]

    point_index_map = _sorting_points_indices(
        mesh.points,
        mesh.connectivity
    )

    cell_index_maps = {}
    point_index_map_inverse = _make_inverse_index_map(point_index_map)
    for cell_type, corners in mesh.connectivity.items():
        for cell_idx, cell_corners in enumerate(corners):
            mapped_cell_corners = point_index_map_inverse[cell_corners]
            corners[cell_idx] = sort_array(mapped_cell_corners)
        cell_index_maps[cell_type] = _sorting_cell_indices(corners)

    sorted_points = mesh.points[point_index_map]
    sorted_cells = {
        cell_type: corners[cell_index_maps[cell_type]]
        for cell_type, corners in mesh.connectivity.items()
    }

    return SortedMesh(
        points=sorted_points,
        connectivity=sorted_cells,
        point_index_map=point_index_map,
        cell_index_maps=cell_index_maps
    )


# TODO(Dennis): this function is pretty incomprehensive and should be refactored
#               priority is not super high though since it is an implementation detail
#               that should not be used outside of the "transform_sorted" function
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
            raise ValueError("Could not find cell")

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


def _sorting_cell_indices(cell_corner_list) -> Array:
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
