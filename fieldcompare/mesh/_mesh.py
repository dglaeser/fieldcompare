"""Class to represent computational meshes"""

from __future__ import annotations
from typing import Iterable, Tuple, Optional

from .._common import _default_base_tolerance
from .._numpy_utils import Array, ArrayLike, as_array
from ..predicates import PredicateResult

from ._mesh_equal import mesh_equal
from ._cell_type import CellType

from . import protocols


class Mesh:
    """
    Represents a computational mesh.

    Args:
        points: The points of the mesh.
        connectivity: The connectivity of the grid cells, specified separately for each cell type.
    """

    def __init__(self, points: ArrayLike, connectivity: Iterable[Tuple[CellType, ArrayLike]]) -> None:
        self._points = as_array(points)
        self._corners = {_get_assert_cell_type(cell_type): as_array(corners) for cell_type, corners in connectivity}
        self._abs_tol = _default_base_tolerance()
        self._rel_tol = _default_base_tolerance()

    @property
    def absolute_tolerance(self) -> float:
        """Return the absolute tolerance defined for equality checks against other meshes."""
        return self._abs_tol

    @property
    def relative_tolerance(self) -> float:
        """Return the relative tolerance defined for equality checks against other meshes."""
        return self._rel_tol

    @property
    def points(self) -> Array:
        """Return the points of this mesh."""
        return self._points

    @property
    def cell_types(self) -> Iterable[CellType]:
        """Return the cell types present in this mesh."""
        return self._corners.keys()

    def connectivity(self, cell_type: CellType) -> Array:
        """
        Return the corner indices array for the cells of the given type.

        Args:
            cell_type: The cell type for which to return the connectivity.
        """
        return self._corners[cell_type]

    def equals(self, other: protocols.Mesh) -> PredicateResult:
        """
        Check whether this mesh is equal to the given one.

        Args:
            other: mesh against with to check equality.
        """
        return mesh_equal(self, other, abs_tol=self._abs_tol, rel_tol=self._rel_tol)

    def set_tolerances(self, abs_tol: Optional[float] = None, rel_tol: Optional[float] = None) -> None:
        """
        Set the tolerances to be used for equality checks against other meshes.

        Args:
            abs_tol: Absolute tolerance to use.
            rel_tol: Relative tolerance to use.
        """
        self._abs_tol = abs_tol if abs_tol is not None else self._abs_tol
        self._rel_tol = rel_tol if rel_tol is not None else self._rel_tol


def _get_assert_cell_type(cell_type: CellType) -> CellType:
    if not isinstance(cell_type, CellType):
        raise TypeError("Cell connectivity has to be given for instances of 'CellType'")
    return cell_type
