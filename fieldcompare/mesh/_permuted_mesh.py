"""Class to represent permuted computational meshes"""
from typing import Iterable, Optional, Dict

from .._array import Array, max_element, make_array, make_uninitialized_array
from ..predicates import PredicateResult

from ._mesh_equal import mesh_equal
from .protocols import Mesh, TransformedMesh


class PermutedMesh(TransformedMesh):
    """Represents a computational mesh, permuted by the given index maps"""
    def __init__(self,
                 mesh: Mesh,
                 point_permutation: Optional[Array] = None,
                 cell_permutations: Optional[Dict[str, Array]] = None) -> None:
        self._mesh = mesh
        self._point_permutation = point_permutation
        self._cell_permutations = cell_permutations
        self._inverse_point_permutation = self._make_inverse_point_permutation()
        self._abs_tol: Optional[float] = None
        self._rel_tol: Optional[float] = None

    @property
    def absolute_tolerance(self) -> float:
        """Return the absolute tolerance defined for equality checks against other meshes"""
        return self._abs_tol if self._abs_tol is not None else self._mesh.absolute_tolerance

    @property
    def relative_tolerance(self) -> float:
        """Return the relative tolerance defined for equality checks against other meshes"""
        return self._rel_tol if self._rel_tol is not None else self._mesh.relative_tolerance

    @property
    def points(self) -> Array:
        """Return the points of this mesh"""
        if self._point_permutation is not None:
            return self._mesh.points[self._point_permutation]
        return self._mesh.points

    @property
    def cell_types(self) -> Iterable[str]:
        """Return the cell types present in this mesh"""
        return self._mesh.cell_types

    def connectivity(self, cell_type: str) -> Array:
        """Return the corner indices array for the cells of the given type"""
        corner_indices = self._mesh.connectivity(cell_type)
        if self._inverse_point_permutation is not None:
            corner_indices = self._inverse_point_permutation[corner_indices]
        return self.transform_cell_data(cell_type, corner_indices)

    def transform_point_data(self, data: Array) -> Array:
        """Transform the given point data values"""
        if self._point_permutation is not None:
            return data[self._point_permutation]
        return data

    def transform_cell_data(self, cell_type: str, data: Array) -> Array:
        """Transform the given cell data values"""
        if self._cell_permutations is not None:
            return data[self._cell_permutations[cell_type]]
        return data

    def equals(self, other: Mesh) -> PredicateResult:
        """Check whether this mesh is equal to the given one"""
        return mesh_equal(
            self, other,
            abs_tol=self.absolute_tolerance,
            rel_tol=self.relative_tolerance,
        )

    def set_tolerances(self,
                       abs_tol: Optional[float] = None,
                       rel_tol: Optional[float] = None) -> None:
        """Set the tolerances used for equality checks against other meshes"""
        self._abs_tol = abs_tol if abs_tol is not None else self._abs_tol
        self._rel_tol = rel_tol if rel_tol is not None else self._rel_tol

    def _make_inverse_point_permutation(self) -> Optional[Array]:
        if self._point_permutation is None:
            return None
        index_map = self._point_permutation
        max_index = max_element(index_map)
        inverse = make_uninitialized_array(max_index+1, dtype=int)
        inverse[index_map] = make_array(list(range(len(index_map))))
        return inverse
