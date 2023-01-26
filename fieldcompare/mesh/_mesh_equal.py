# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Equality check for computational meshes"""
from typing import Optional

from .._numpy_utils import Array, make_array, get_sorting_index_map
from ..predicates import FuzzyEquality, ExactEquality, PredicateResult
from .protocols import Mesh as MeshInterface


def mesh_equal(
    source: MeshInterface,
    target: MeshInterface,
    rel_tol: Optional[float] = None,
    abs_tol: Optional[float] = None,
) -> PredicateResult:
    """Check whether two meshes are equal"""
    rel_tol = min(source.relative_tolerance, target.relative_tolerance) if rel_tol is None else rel_tol
    abs_tol = min(source.absolute_tolerance, target.absolute_tolerance) if abs_tol is None else abs_tol
    points_equal = FuzzyEquality(rel_tol=rel_tol, abs_tol=abs_tol)(source.points, target.points)
    if not points_equal:
        return PredicateResult(False, report=f"Differing points - '{points_equal.report}'")
    if not set(source.cell_types) == set(target.cell_types):
        return PredicateResult(False, report="Differing grid cell types detected")
    for cell_type in source.cell_types:
        if len(source.connectivity(cell_type)) != len(target.connectivity(cell_type)):
            return PredicateResult(False, report=f"Differing number of cells of type '{cell_type.name}'")
        if not ExactEquality()(
            _get_sorted_corner_indices(source.connectivity(cell_type)),
            _get_sorted_corner_indices(target.connectivity(cell_type)),
        ):
            return PredicateResult(False, report=f"Differing connectivity detected for cell of type '{cell_type.name}'")
    return PredicateResult(True)


def _get_sorted_corner_indices(corners: Array) -> Array:
    if len(corners.shape) == 2:
        return _get_fixed_size_corner_indices_sorted(corners)
    elif len(corners.shape) == 1:
        return _get_dynamic_size_corner_indices_sorted(corners)
    raise ValueError("Unsupported connectivity array shape")


def _get_fixed_size_corner_indices_sorted(corners: Array) -> Array:
    sorted_corners = make_array(corners)
    for i in range(len(sorted_corners)):
        sorted_corners[i].sort()
    return sorted_corners


def _get_dynamic_size_corner_indices_sorted(corners: Array) -> Array:
    return make_array([c[get_sorting_index_map(c)] for c in corners], dtype="object")
