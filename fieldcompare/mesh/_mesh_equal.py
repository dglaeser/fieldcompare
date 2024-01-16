# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Equality check for computational meshes"""
from __future__ import annotations
from itertools import product

from .._numpy_utils import Array, make_array, get_sorting_index_map
from ..predicates import FuzzyEquality, ExactEquality, PredicateResult
from ._cell_type import CellType
from .protocols import Mesh as MeshInterface


def mesh_equal(
    source: MeshInterface,
    target: MeshInterface,
    rel_tol: float | None = None,
    abs_tol: float | None = None,
) -> PredicateResult:
    """Check whether two meshes are equal"""
    rel_tol = min(source.relative_tolerance, target.relative_tolerance) if rel_tol is None else rel_tol
    abs_tol = min(source.absolute_tolerance, target.absolute_tolerance) if abs_tol is None else abs_tol
    points_equal = FuzzyEquality(rel_tol=rel_tol, abs_tol=abs_tol)(source.points, target.points)
    if not points_equal:
        return PredicateResult(False, report=f"Differing points - '{points_equal.report}'")

    source_ct, target_ct = set(source.cell_types), set(target.cell_types)
    diff = source_ct.difference(target_ct).union(target_ct.difference(source_ct))
    if len(_without_compatibles(diff)) != 0:
        return PredicateResult(False, report="Differing grid cell types detected")

    for cell_type in source.cell_types:
        tct = cell_type if cell_type in target_ct else _find_compatible(target_ct, cell_type)
        if len(source.connectivity(cell_type)) != len(target.connectivity(tct)):
            message_end = f"type '{tct.name}'" if tct == cell_type else f"types '{cell_type.name}/{tct.name}'"
            return PredicateResult(False, report=f"Differing number of cells of {message_end}")
        if not ExactEquality()(
            _get_sorted_corner_indices(source.connectivity(cell_type)),
            _get_sorted_corner_indices(target.connectivity(tct)),
        ):
            return PredicateResult(False, report=f"Differing connectivity detected for cell of type '{cell_type.name}'")
    return PredicateResult(True)


_FIXED_SIZE_CORNER_DIM = 2
_DYNAMIC_SIZE_CORNER_DIM = 1


def _get_sorted_corner_indices(corners: Array) -> Array:
    if len(corners.shape) == _FIXED_SIZE_CORNER_DIM:
        return _get_fixed_size_corner_indices_sorted(corners)
    if len(corners.shape) == _DYNAMIC_SIZE_CORNER_DIM:
        return _get_dynamic_size_corner_indices_sorted(corners)
    raise ValueError("Unsupported connectivity array shape")


def _get_fixed_size_corner_indices_sorted(corners: Array) -> Array:
    sorted_corners = make_array(corners)
    for i in range(len(sorted_corners)):
        sorted_corners[i].sort()
    return sorted_corners


def _get_dynamic_size_corner_indices_sorted(corners: Array) -> Array:
    return make_array([c[get_sorting_index_map(c)] for c in corners], dtype="object")


def _without_compatibles(cts: set[CellType]) -> set[CellType]:
    to_remove: set[CellType] = set()
    for c1, c2 in product(cts, cts):
        if c1.is_compatible_with(c2):
            to_remove = to_remove.union(set([c1, c2]))
    return cts.difference(to_remove)


def _find_compatible(cts: set[CellType], ct: CellType) -> CellType:
    for c in cts:
        if c.is_compatible_with(ct):
            return c
    raise RuntimeError("Could not find compatible cell type")
