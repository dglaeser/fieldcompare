# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Mesh permutation functions"""

from __future__ import annotations
from copy import deepcopy

from .._numpy_utils import (
    Array,
    flatten,
    any_true,
    sub_array,
    accumulate,
    append_to_array,
    get_sorting_index_map,
    get_lex_sorting_index_map,
    get_fuzzy_lex_sorting_index_map,
    fuzzy_equal,
    walk_adjacent_true_index_ranges,
    make_initialized_array,
    make_array,
    concatenate,
    make_zeros,
)

from ._cell_type import CellType
from ._mesh import Mesh
from ._permuted_mesh import PermutedMesh
from ._mesh_fields import MeshFields, TransformedMeshFields, remove_cell_type_suffix

from . import protocols


def extend_space_dimension_to(space_dimension: int, mesh_fields: protocols.MeshFields) -> protocols.MeshFields:
    """
    Extend the space dimension of the grid by appending zeroes. Extends vector/tensor fields whose dimensions are
    smaller than `space_dimension`.

    Args:
        space_dimension: the target space dimension.
        mesh_fields: the mesh fields to be transformed.
    """
    mesh_space_dim = mesh_fields.domain.points.shape[1]
    if space_dimension == mesh_space_dim:
        return mesh_fields
    if space_dimension < mesh_space_dim:
        raise ValueError("Given space dimension smaller than that of the mesh")

    def _resized_vector_field_values(values: Array) -> Array:
        if values.shape[1] < space_dimension:
            result = make_zeros(shape=(values.shape[0], space_dimension), dtype=values.dtype)
            result[:, :mesh_space_dim] = values
            return result
        return values

    def _resized_tensor_field_values(values: Array) -> Array:
        if values.shape[1] < space_dimension and values.shape[2] < space_dimension:
            result = make_zeros(shape=(values.shape[0], space_dimension, space_dimension), dtype=values.dtype)
            result[:, :mesh_space_dim, :mesh_space_dim] = values
            return result
        return values

    def _resized_field_values(values: Array) -> Array:
        if _is_scalar_field(values):
            return values
        if _is_vector_field(values):
            return _resized_vector_field_values(values)
        if _is_tensor_field(values):
            return _resized_tensor_field_values(values)
        raise ValueError(f"Unsupported field shape: {values.shape}")

    def _resized_cell_fields():
        cell_fields = {}
        cell_types = [ct for ct in mesh_fields.domain.cell_types]
        for field, cell_type in mesh_fields.cell_fields_types:
            name = remove_cell_type_suffix(cell_type, field.name)
            if name not in cell_fields:
                cell_fields[name] = [[] for _ in range(len(cell_types))]
            cell_fields[name][cell_types.index(cell_type)] = _resized_field_values(field.values)
        return cell_fields

    extended_mesh = Mesh(
        points=_resized_vector_field_values(mesh_fields.domain.points),
        connectivity=[
            (cell_type, mesh_fields.domain.connectivity(cell_type)) for cell_type in mesh_fields.domain.cell_types
        ],
    )
    extended_mesh.set_tolerances(
        abs_tol=mesh_fields.domain.absolute_tolerance, rel_tol=mesh_fields.domain.relative_tolerance
    )

    return MeshFields(
        mesh=extended_mesh,
        point_data={f.name: _resized_field_values(f.values) for f in mesh_fields.point_fields},
        cell_data=_resized_cell_fields(),
    )


def sort(mesh_fields: protocols.MeshFields) -> protocols.MeshFields:
    """
    Sort the given mesh fields to arrive at a unique representation.

    Args:
        mesh_fields: The mesh fields to be sorted.
    """
    return sort_cells(sort_points(strip_orphan_points(mesh_fields)))


def merge(*mesh_fields: protocols.MeshFields, remove_duplicate_points: bool = True) -> protocols.MeshFields:
    """
    Merge the given mesh fields into a single one.

    Args:
        mesh_fields: the mesh fields to be merged.
        remove_duplicate_points: if set to true, duplicate points between the meshes are removed.
                                 Points and associated field values are taken from those meshes
                                 that come first in the provided list of arguments.
    """
    result: protocols.MeshFields | None = None
    for i, fields in enumerate(mesh_fields):
        if i == 0:
            result = fields
        else:
            assert result is not None
            result = _merge(result, fields, remove_duplicate_points)
    assert result is not None
    return result


def strip_orphan_points(fields: protocols.MeshFields) -> protocols.MeshFields:
    """Remove unconnected points from the given mesh fields"""
    return TransformedMeshFields(
        field_data=fields,
        transformation=lambda mesh: PermutedMesh(mesh=mesh, point_permutation=_unconnected_points_filter_map(mesh)),
    )


def sort_points(fields: protocols.MeshFields) -> protocols.MeshFields:
    """Sort the mesh points by their coordinates (lexicographically)"""

    def _get_permuted(mesh: protocols.Mesh) -> PermutedMesh:
        point_map = _sorting_points_indices(
            points=mesh.points,
            cells={ct: mesh.connectivity(ct) for ct in mesh.cell_types},
            abs_tol=mesh.absolute_tolerance,
            rel_tol=mesh.relative_tolerance,
        )
        return PermutedMesh(mesh=mesh, point_permutation=point_map)

    return TransformedMeshFields(field_data=fields, transformation=lambda mesh: _get_permuted(mesh))


def sort_cells(fields: protocols.MeshFields) -> protocols.MeshFields:
    """Sort the cells of the mesh by their connectivity (lexicographically)"""
    return TransformedMeshFields(
        field_data=fields,
        transformation=lambda mesh: PermutedMesh(
            mesh=mesh,
            cell_permutations={
                ct: _get_cell_corners_sorting_index_map(mesh.connectivity(ct)) for ct in mesh.cell_types
            },
        ),
    )


def _unconnected_points_filter_map(mesh: protocols.Mesh) -> Array:
    is_unconnected = make_initialized_array(size=len(mesh.points), dtype=bool, init_value=True)
    for cell_type in mesh.cell_types:
        for point_index in flatten(mesh.connectivity(cell_type)):
            is_unconnected[point_index] = False

    num_unconnected = accumulate(is_unconnected)
    first_unconnected_after_sort = int(len(is_unconnected) - num_unconnected)
    unconnected_filter_map = get_sorting_index_map(is_unconnected)
    unconnected_filter_map = sub_array(unconnected_filter_map, 0, first_unconnected_after_sort)
    return unconnected_filter_map


def _get_cell_corners_sorting_index_map(corners_array: Array) -> Array:
    hashes = make_array([hash(tuple(sorted(corners))) for corners in corners_array])
    return get_sorting_index_map(hashes)


def _sorting_points_indices(points, cells, rel_tol: float, abs_tol: float) -> Array:
    if points.shape[0] == 0:
        return make_array([], dtype=int)

    idx_map = get_fuzzy_lex_sorting_index_map(points, abs_tol=abs_tol, rel_tol=rel_tol)

    # find fuzzy equal neighboring points (may happen for non-conforming meshes)
    zero_diffs = fuzzy_equal(points[idx_map][:-1], points[idx_map][1:], abs_tol=abs_tol, rel_tol=rel_tol).all(axis=1)
    zero_diffs = append_to_array(zero_diffs, False)

    if any_true(zero_diffs):
        # sort the chunks of equal points by sorting them according
        # to the "minimum" position of the cell centers around it
        point_to_cells_map = _get_points_to_cell_indices_map(cells, len(points))

        def _compute_cell_center(cell_type: CellType, cell_index: int):
            cell_corner_list = cells[cell_type][cell_index]
            return accumulate(points[cell_corner_list], axis=0) / len(cell_corner_list)

        def _get_min_cell_center_around_point(point_idx):
            adjacent_cells = [(ct, index) for ct in cells for index in point_to_cells_map[ct][point_idx]]
            if len(adjacent_cells) == 0:
                raise ValueError("Cannot uniquely sort duplicate points that are not connected to any cells")
            centers = make_array(
                [_compute_cell_center(cell_type, cell_index) for cell_type, cell_index in adjacent_cells]
            )
            return centers[get_fuzzy_lex_sorting_index_map(centers, abs_tol=abs_tol, rel_tol=rel_tol)[0]]

        for start, end in walk_adjacent_true_index_ranges(zero_diffs):
            min_cell_centers = make_array([_get_min_cell_center_around_point(idx_map[i]) for i in range(start, end)])
            sorted_by_min_cell_center = get_fuzzy_lex_sorting_index_map(
                min_cell_centers, abs_tol=abs_tol, rel_tol=rel_tol
            )
            idx_map[start:end] = idx_map[start:end][sorted_by_min_cell_center]
    return make_array(idx_map)


def _get_points_to_cell_indices_map(cells, num_points) -> dict[CellType, list]:
    def _get_cells_around_points(_cells) -> list:
        result: list = [[] for _ in range(num_points)]
        for cell_idx, _corners in enumerate(_cells):
            for _corner_idx in _corners:
                result[_corner_idx].append(cell_idx)
        return result

    return {cell_type: _get_cells_around_points(corners) for cell_type, corners in cells.items()}


def _merge(
    fields1: protocols.MeshFields, fields2: protocols.MeshFields, remove_duplicate_points: bool
) -> protocols.MeshFields:
    duplicate_point_idx_map = (
        _map_duplicate_points(source=fields2.domain, target=fields1.domain) if remove_duplicate_points else {}
    )
    points2_filter = _filter_external_indices(
        num_values=len(fields2.domain.points), external_indices=duplicate_point_idx_map
    )
    points2_map = _map_external_indices(
        num_values=len(fields2.domain.points),
        external_indices_map=duplicate_point_idx_map,
        external_indices_offset=len(fields1.domain.points),
    )

    if len(points2_filter) == 0:
        return fields1

    # merged points
    points = concatenate((fields1.domain.points, fields2.domain.points[points2_filter]))

    # merged cell connectivities
    cells_dict: dict[CellType, Array] = {
        ct: make_array(fields1.domain.connectivity(ct)) for ct in fields1.domain.cell_types
    }
    for ct in fields2.domain.cell_types:
        mapped_connectivity = make_array(fields2.domain.connectivity(ct))
        for cell_idx, cell_corners in enumerate(mapped_connectivity):
            mapped_connectivity[cell_idx] = points2_map[cell_corners]
        if ct in cells_dict:
            cells_dict[ct] = concatenate((cells_dict[ct], mapped_connectivity))
        else:
            cells_dict[ct] = mapped_connectivity

    # merged cell fields
    raw_cell_field_names = set()
    cell_fields: dict[CellType, dict[str, Array]] = {ct: {} for ct in cells_dict}
    for field, ct in fields1.cell_fields_types:
        raw_field_name = remove_cell_type_suffix(ct, field.name)
        cell_fields[ct][raw_field_name] = field.values
        raw_cell_field_names.add(raw_field_name)
    for field, ct in fields2.cell_fields_types:
        raw_field_name = remove_cell_type_suffix(ct, field.name)
        raw_cell_field_names.add(raw_field_name)
        if raw_field_name in cell_fields[ct]:
            cell_fields[ct][raw_field_name] = concatenate((cell_fields[ct][raw_field_name], field.values))
        else:
            cell_fields[ct][raw_field_name] = field.values

    # merged point fields
    point_fields1: dict[str, Array] = {f.name: f.values for f in fields1.point_fields}
    point_fields2: dict[str, Array] = {f.name: f.values[points2_filter] for f in fields2.point_fields}
    point_fields: dict[str, Array] = {}
    for name in point_fields1:
        if name in point_fields2:
            point_fields[name] = concatenate((point_fields1[name], point_fields2[name]))
        else:
            zero = make_zeros(shape=point_fields1[name].shape[1:], dtype=point_fields1[name].dtype)
            point_fields[name] = concatenate(
                (
                    make_array(point_fields1[name]),
                    make_array(
                        [deepcopy(zero) for _ in range(len(fields2.domain.points))], dtype=point_fields1[name].dtype
                    ),
                )
            )
    for name in filter(lambda n: n not in point_fields, point_fields2):
        zero = make_zeros(shape=point_fields2[name].shape[1:], dtype=point_fields2[name].dtype)
        point_fields[name] = concatenate(
            (
                make_array(
                    [deepcopy(zero) for _ in range(len(fields1.domain.points))], dtype=point_fields2[name].dtype
                ),
                make_array(point_fields2[name]),
            )
        )

    return MeshFields(
        mesh=Mesh(points=points, connectivity=((ct, connectivity) for ct, connectivity in cells_dict.items())),
        point_data={name: values for name, values in point_fields.items()},
        cell_data={name: [cell_fields[ct][name] for ct in cells_dict] for name in raw_cell_field_names},
    )


def _map_duplicate_points(source: protocols.Mesh, target: protocols.Mesh) -> dict[int, int]:
    sort_idx_map_source = get_lex_sorting_index_map(source.points)

    def _is_lex_smaller(p1: Array, p2: Array) -> bool:
        for x1, x2 in zip(p1, p2):
            if x1 < x2:
                return True
            if x1 > x2:
                return False
        return False

    def _find_candidate(target_point: Array) -> int | None:
        lower = 0
        upper = len(source.points)
        while lower < upper:
            mid = (lower + upper) // 2
            mid_mapped = sort_idx_map_source[mid]
            if _is_lex_smaller(source.points[mid_mapped], target_point):
                lower = mid + 1
            else:
                upper = mid
        return sort_idx_map_source[lower] if lower < len(source.points) else None

    result = {}
    for pidx_target in range(len(target.points)):
        equal_candidate_idx = _find_candidate(target.points[pidx_target])
        if equal_candidate_idx is None:
            continue
        if (source.points[equal_candidate_idx] == target.points[pidx_target]).all():
            result[equal_candidate_idx] = pidx_target
    return result


def _filter_external_indices(num_values: int, external_indices) -> Array:
    return make_array([i for i in range(num_values) if i not in external_indices])


def _map_external_indices(num_values: int, external_indices_map: dict[int, int], external_indices_offset: int) -> Array:
    result = make_array([i for i in range(num_values)])
    mapped_index_offset = 0
    for i in range(num_values):
        if i in external_indices_map:
            result[i] = external_indices_map[i]
            mapped_index_offset += 1
        else:
            result[i] = result[i] + external_indices_offset - mapped_index_offset
    return result


def _is_scalar_field(field: Array) -> bool:
    return len(field.shape) == 1 or (len(field.shape) == 2 and field.shape[1] == 1)


def _is_vector_field(field: Array) -> bool:
    return len(field.shape) == 2


def _is_tensor_field(field: Array) -> bool:
    return len(field.shape) == 3
