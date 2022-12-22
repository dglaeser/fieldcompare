"""Mesh permutation functions"""

from copy import deepcopy
from typing import Dict, Optional

from .._numpy_utils import (
    Array,
    flatten,
    any_true,
    all_true,
    sub_array,
    abs_array,
    accumulate,
    min_element,
    max_element,
    adjacent_difference,
    append_to_array,
    elements_less,
    get_sorting_index_map,
    get_lex_sorting_index_map,
    make_initialized_array,
    make_array,
    concatenate,
    make_zeros
)

from .._common import _default_base_tolerance
from ._cell_type import CellType
from ._mesh import Mesh
from ._permuted_mesh import PermutedMesh
from ._mesh_fields import MeshFields, TransformedMeshFields, remove_cell_type_suffix

from . import protocols


def sort(mesh_fields: protocols.MeshFields) -> protocols.MeshFields:
    """
    Sort the given mesh fields to arrive at a unique representation.

    Args:
        mesh_fields: The mesh fields to be sorted.
    """
    return sort_cells(sort_points(strip_orphan_points(mesh_fields)))


def merge(*mesh_fields: protocols.MeshFields) -> protocols.MeshFields:
    """
    Merge the given mesh fields into a single one

    Args:
        mesh_fields: the mesh fields to be merged.
    """
    result: Optional[protocols.MeshFields] = None
    for i, fields in enumerate(mesh_fields):
        if i == 0:
            result = fields
        else:
            assert result is not None
            result = _merge(result, fields)
    assert result is not None
    return result


def strip_orphan_points(fields: protocols.MeshFields) -> protocols.MeshFields:
    """Remove unconnected points from the given mesh fields and return the result"""
    return TransformedMeshFields(
        field_data=fields,
        transformation=lambda mesh: PermutedMesh(
            mesh=mesh,
            point_permutation=_unconnected_points_filter_map(mesh)
        )
    )


def sort_points(fields: protocols.MeshFields) -> protocols.MeshFields:
    """Sorts the mesh points by their coordinates (lexicographically)"""
    try:
        def _get_permuted(mesh: protocols.Mesh) -> PermutedMesh:
            point_map = _sorting_points_indices(
                mesh.points,
                {ct: mesh.connectivity(ct) for ct in mesh.cell_types}
            )
            return PermutedMesh(mesh=mesh, point_permutation=point_map)

        return TransformedMeshFields(
            field_data=fields,
            transformation=lambda mesh: _get_permuted(mesh)
        )
    except ValueError as e:
        if len(_unconnected_points_filter_map(fields.domain)) != len(fields.domain.points):
            raise ValueError(
                "Could not sort the point coordinates. Your mesh seems to have\n"
                "unconnected points, which is known to cause the sorting algorithm\n"
                "on non-conforming meshes. In this case, make sure to first strip the\n"
                "mesh of all unconnected points, for instance, using the respective\n"
                "transformation provided."
            )
        raise ValueError(f"Caught an exception when sorting the mesh points: {e}")


def sort_cells(fields: protocols.MeshFields) -> protocols.MeshFields:
    """Sorts the cells of the map by their connectivity (lexicographically)"""
    return TransformedMeshFields(
        field_data=fields,
        transformation=lambda mesh: PermutedMesh(
            mesh=mesh,
            cell_permutations={
                ct: _get_cell_corners_sorting_index_map(mesh.connectivity(ct))
                for ct in mesh.cell_types
            }
        )
    )


def _unconnected_points_filter_map(mesh: protocols.Mesh) -> Array:
    is_unconnected = make_initialized_array(
        size=len(mesh.points),
        dtype=bool,
        init_value=True
    )
    for cell_type in mesh.cell_types:
        for point_index in flatten(mesh.connectivity(cell_type)):
            is_unconnected[point_index] = False

    num_unconnected = accumulate(is_unconnected)
    first_unconnected_after_sort = int(len(is_unconnected) - num_unconnected)
    unconnected_filter_map = get_sorting_index_map(is_unconnected)
    unconnected_filter_map = sub_array(unconnected_filter_map, 0, first_unconnected_after_sort)
    return unconnected_filter_map


def _get_cell_corners_sorting_index_map(corners_array: Array) -> Array:
    sorted_by_hash = list(range(len(corners_array)))
    sorted_by_hash.sort(key=lambda i: hash(tuple(sorted(corners_array[i]))))
    return make_array(sorted_by_hash)


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

        def _compute_cell_center(cell_type: CellType, cell_index: int):
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


def _get_points_to_cell_indices_map(cells, num_points) -> Dict[CellType, list]:
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


def _merge(fields1: protocols.MeshFields,
           fields2: protocols.MeshFields) -> MeshFields:
    points = concatenate((
        fields1.domain.points,
        fields2.domain.points
    ))

    # merged cell connectivities
    points2_offset = len(fields1.domain.points)
    cells_dict: Dict[CellType, Array] = {
        ct: make_array(fields1.domain.connectivity(ct))
        for ct in fields1.domain.cell_types
    }
    for ct in fields2.domain.cell_types:
        connectivity_with_offset = make_array(fields2.domain.connectivity(ct) + points2_offset)
        if ct in cells_dict:
            cells_dict[ct] = concatenate((cells_dict[ct], connectivity_with_offset))
        else:
            cells_dict[ct] = connectivity_with_offset

    # merged cell fields
    raw_cell_field_names = set()
    cell_fields: Dict[CellType, Dict[str, Array]] = {ct: {} for ct in cells_dict}
    for field, ct in fields1.cell_fields_types:
        raw_field_name = remove_cell_type_suffix(ct, field.name)
        cell_fields[ct][raw_field_name] = field.values
        raw_cell_field_names.add(raw_field_name)
    for field, ct in fields2.cell_fields_types:
        raw_field_name = remove_cell_type_suffix(ct, field.name)
        raw_cell_field_names.add(raw_field_name)
        if raw_field_name in cell_fields[ct]:
            cell_fields[ct][raw_field_name] = concatenate((
                cell_fields[ct][raw_field_name],
                field.values
            ))
        else:
            cell_fields[ct][raw_field_name] = field.values

    # merged point fields
    point_fields1: Dict[str, Array] = {f.name: f.values for f in fields1.point_fields}
    point_fields2: Dict[str, Array] = {f.name: f.values for f in fields2.point_fields}
    point_fields: Dict[str, Array] = {}
    for name in point_fields1:
        if name in point_fields2:
            point_fields[name] = concatenate((point_fields1[name], point_fields2[name]))
        else:
            zero = make_zeros(shape=point_fields1[name].shape[1:], dtype=point_fields1[name].dtype)
            point_fields[name] = concatenate((
                make_array(point_fields1[name]),
                make_array(
                    [deepcopy(zero) for _ in range(len(fields2.domain.points))],
                    dtype=point_fields1[name].dtype
                )
            ))
    for name in filter(lambda n: n not in point_fields, point_fields2):
        zero = make_zeros(shape=point_fields2[name].shape[1:], dtype=point_fields2[name].dtype)
        point_fields[name] = concatenate((
            make_array(
                [deepcopy(zero) for _ in range(points2_offset)],
                dtype=point_fields2[name].dtype
            ),
            make_array(point_fields2[name])
        ))

    return MeshFields(
        mesh=Mesh(
            points=points,
            connectivity=((ct, connectivity) for ct, connectivity in cells_dict.items())
        ),
        point_data={name: values for name, values in point_fields.items()},
        cell_data={
            name: [cell_fields[ct][name] for ct in cells_dict]
            for name in raw_cell_field_names
        }
    )
