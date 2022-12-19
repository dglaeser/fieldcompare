"""Class to represent computational meshes"""

from typing import Iterable, Tuple, Optional

from .._common import _default_base_tolerance
from .._numpy_utils import Array, ArrayLike, as_array
from ..predicates import PredicateResult

from .protocols import Mesh as MeshInterface
from ._mesh_equal import mesh_equal


class Mesh:
    """Represents a computational mesh"""
    def __init__(self,
                 points: ArrayLike,
                 connectivity: Iterable[Tuple[str, ArrayLike]]) -> None:
        self._points = as_array(points)
        self._corners = {
            cell_type: as_array(corners)
            for cell_type, corners in connectivity
        }
        self._abs_tol = _default_base_tolerance()
        self._rel_tol = _default_base_tolerance()

    @property
    def absolute_tolerance(self) -> float:
        """Return the absolute tolerance defined for equality checks against other meshes"""
        return self._abs_tol

    @property
    def relative_tolerance(self) -> float:
        """Return the relative tolerance defined for equality checks against other meshes"""
        return self._rel_tol

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
        return mesh_equal(self, other, abs_tol=self._abs_tol, rel_tol=self._rel_tol)

    def set_tolerances(self,
                       abs_tol: Optional[float] = None,
                       rel_tol: Optional[float] = None) -> None:
        """Set the tolerances used for equality checks against other meshes"""
        self._abs_tol = abs_tol if abs_tol is not None else self._abs_tol
        self._rel_tol = rel_tol if rel_tol is not None else self._rel_tol
