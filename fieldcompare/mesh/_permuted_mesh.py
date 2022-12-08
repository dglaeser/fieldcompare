"""Class to represent permuted computational meshes"""
from typing import Iterable, Optional, Dict
from .._array import Array, max_element, make_array, make_uninitialized_array
from .protocols import Mesh


class PermutedMesh:
    """Represents a permuted computational mesh"""
    def __init__(self,
                 mesh: Mesh,
                 point_permutation: Optional[Array] = None,
                 cell_permutations: Optional[Dict[str, Array]] = None) -> None:
        self._mesh = mesh
        self._point_permutation = point_permutation
        self._cell_permutations = cell_permutations
        self._inverse_point_permutation = self._make_inverse_point_permutation()

    @property
    def points(self) -> Array:
        """Return the points of this mesh"""
        return self.permute_point_data(self._mesh.points)

    @property
    def cell_types(self) -> Iterable[str]:
        """Return the cell types present in this mesh"""
        return self._mesh.cell_types

    def connectivity(self, cell_type: str) -> Array:
        """Return the corner indices array for the cells of the given type"""
        corner_indices = self._mesh.connectivity(cell_type)
        if self._inverse_point_permutation is not None:
            corner_indices = self._inverse_point_permutation[corner_indices]
        return self.permute_cell_data(cell_type, corner_indices)

    def permute_point_data(self, data: Array) -> Array:
        """Permute the given point data values"""
        if self._point_permutation is not None:
            return data[self._point_permutation]
        return data

    def permute_cell_data(self, cell_type: str, data: Array) -> Array:
        """Permute the given cell data values"""
        if self._cell_permutations is not None:
            print("D = ", data)
            print("P = ", self._cell_permutations[cell_type])
            return data[self._cell_permutations[cell_type]]
        return data

    def _make_inverse_point_permutation(self) -> Optional[Array]:
        if self._point_permutation is None:
            return None
        index_map = self._point_permutation
        max_index = max_element(index_map)
        inverse = make_uninitialized_array(max_index+1, dtype=int)
        inverse[index_map] = make_array(list(range(len(index_map))))
        return inverse
