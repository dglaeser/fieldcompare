"""Equality check for computational meshes"""

from .._common import _default_base_tolerance
from ..predicates import FuzzyEquality, ExactEquality, PredicateResult
from .protocols import Mesh as MeshInterface


def mesh_equal(
    source: MeshInterface,
    target: MeshInterface,
    rel_tol: float = _default_base_tolerance(),
    abs_tol: float = _default_base_tolerance(),
) -> PredicateResult:
    """Check whether two meshes are equal"""
    points_equal = FuzzyEquality(rel_tol=rel_tol, abs_tol=abs_tol)(source.points, target.points)
    if not points_equal:
        return PredicateResult(False, report=f"Differing points - '{points_equal.report}'")
    if not set(source.cell_types) == set(target.cell_types):
        return PredicateResult(False, report="Differing grid cell types detected")
    for cell_type in source.cell_types:
        if len(source.connectivity(cell_type)) != len(target.connectivity(cell_type)):
            return PredicateResult(False, report=f"Differing number of cells of type '{cell_type}'")
        if not all(
            ExactEquality()(sorted(source_corners), sorted(target_corners))
            for source_corners, target_corners in zip(source.connectivity(cell_type), target.connectivity(cell_type))
        ):
            return PredicateResult(False, report=f"Differing connectivity detected for cell of type '{cell_type}'")
    return PredicateResult(True)
