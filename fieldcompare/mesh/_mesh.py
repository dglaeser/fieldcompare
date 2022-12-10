"""Class to represent computational meshes"""
from typing import Iterable, Tuple
from .._array import Array, ArrayLike, make_array
from ..predicates import FuzzyEquality, PredicateResult
from .protocols import Mesh as MeshInterface

class Mesh:
    """Represents a computational mesh"""
    def __init__(self,
                 points: ArrayLike,
                 connectivity: Iterable[Tuple[str, ArrayLike]]) -> None:
        self._points = make_array(points)
        self._corners = {
            cell_type: make_array(corners)
            for cell_type, corners in connectivity
        }

    @property
    def points(self) -> Array:
        """Return the points of this mesh"""
        return self._points

    @property
    def cell_types(self) -> Iterable[str]:
        """Return the cell types present in this mesh"""
        return self._corners.keys()

    def connectivity(self, cell_type: str) -> Array:
        """Return the corner indices array for the cells of the given type"""
        return self._corners[cell_type]

    def equals(self, other: MeshInterface) -> PredicateResult:
        """Check whether this mesh is equal to the given one"""
        points_equal = FuzzyEquality()(self.points, other.points)
        if not points_equal:
            return PredicateResult(
                False,
                report=f"Differing point coordinates: {points_equal.report}"
            )
        if not set(self.cell_types) == set(other.cell_types):
            return PredicateResult(
                False,
                report="Differing grid cell types detected"
            )
        for cell_type in self.cell_types:
            if len(self.connectivity(cell_type)) != len(other.connectivity(cell_type)):
                return PredicateResult(
                    False,
                    report=f"Differing connectivity for '{cell_type}' detected"
                )
        return PredicateResult(True)
