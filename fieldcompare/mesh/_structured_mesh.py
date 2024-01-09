# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Class to represent structured computational meshes"""

from __future__ import annotations
from typing import Iterable, Tuple, List
from functools import reduce
from operator import mul

from ..predicates import FuzzyEquality, PredicateResult
from ..protocols import DynamicTolerance
from .._numpy_utils import Array, ArrayLike, as_array, max_abs_value

from ._mesh import default_mesh_relative_tolerance
from ._mesh_equal import mesh_equal
from ._cell_type import CellType, CellTypes

from . import protocols


_VTK_DIMENSION = 3


class StructuredMesh:
    """
    Represents a structured computational mesh.

    Args:
        extents: The number of cells per coordinate direction
        points: The points of the structured mesh
    """

    def __init__(self, extents: Tuple[int, int, int], points: ArrayLike) -> None:
        self._extents = extents
        self._points = as_array(points)
        self._dimension = len(self._nonzero_extents())

        if len(extents) != _VTK_DIMENSION:
            raise ValueError(f"Expected three-dimensional extents tuple, got {extents}")

        expected_num_points = self._accumulate(map(lambda e: e + 1, extents))
        if len(self._points) != expected_num_points:
            raise ValueError(
                f"Number of points, computed from the given extents ({extents}), "
                f"is {expected_num_points}, but the given point array has length {len(self._points)}"
            )
        self._rel_tol = default_mesh_relative_tolerance()
        self._abs_tol = max_abs_value(self._points) * default_mesh_relative_tolerance()

    @property
    def extents(self) -> Tuple[int, int, int]:
        """Return the number of cells in each coordinate direction"""
        return self._extents

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
        if self._dimension == 1:  # noqa: PLR2004
            return [CellTypes.line]
        return [CellTypes.quad] if self._dimension == 2 else [CellTypes.hexahedron]  # noqa: PLR2004

    def connectivity(self, cell_type: CellType) -> Array:
        """
        Return the corner indices array for the cells of the given type.

        Args:
            cell_type: The cell type for which to return the connectivity.
        """
        if self._dimension == 1:  # noqa: PLR2004
            if cell_type != CellTypes.line:
                raise ValueError(f"Unexpected cell type {cell_type}. Expected {CellTypes.line}")
            return as_array([[i, i + 1] for i in range(self._num_cells())])

        cells = []
        nonzero_extents = self._nonzero_extents()
        xoffset = nonzero_extents[0] + 1
        if self._dimension == 2:  # noqa: PLR2004
            for j in range(nonzero_extents[1]):
                for i in range(nonzero_extents[0]):
                    p0 = j * xoffset + i
                    cells.append([p0, p0 + 1, p0 + xoffset + 1, p0 + xoffset])
            return as_array(cells)

        xyoffset = xoffset * (nonzero_extents[1] + 1)
        for k in range(nonzero_extents[2]):
            for j in range(nonzero_extents[1]):
                for i in range(nonzero_extents[0]):
                    p0 = k * xyoffset + j * xoffset + i
                    base_quad = [p0, p0 + 1, p0 + xoffset + 1, p0 + xoffset]
                    cells.append(base_quad + [i + xyoffset for i in base_quad])
        return as_array(cells)

    def equals(self, other: protocols.Mesh) -> PredicateResult:
        """
        Check whether this mesh is equal to the given one.

        Args:
            other: mesh against with to check equality.
        """
        if not isinstance(other, StructuredMesh):
            return mesh_equal(self, other)

        if self._extents != other._extents:
            return PredicateResult(False, report=f"Different structured grid extents: {self.extents} - {other.extents}")

        points_equal = FuzzyEquality(rel_tol=self.relative_tolerance, abs_tol=self.absolute_tolerance)(
            self.points, other.points
        )
        if not points_equal:
            return PredicateResult(False, report=f"Differing points - '{points_equal.report}'")
        return PredicateResult(True)

    def set_tolerances(
        self,
        abs_tol: float | DynamicTolerance | None = None,
        rel_tol: float | DynamicTolerance | None = None,
    ) -> None:
        """
        Set the tolerances to be used for equality checks against other meshes.

        Args:
            abs_tol: Absolute tolerance to use.
            rel_tol: Relative tolerance to use.
        """
        self._rel_tol = self._rel_tol if rel_tol is None else self._get_tolerance(rel_tol)
        self._abs_tol = self._abs_tol if abs_tol is None else self._get_tolerance(abs_tol)

    def _get_tolerance(self, tol: float | DynamicTolerance) -> float:
        result = tol(self._points, self._points) if isinstance(tol, DynamicTolerance) else tol
        assert isinstance(result, float)
        return result

    def _num_cells(self) -> int:
        return self._accumulate(self._nonzero_extents())

    def _nonzero_extents(self) -> List[int]:
        return list([e for e in self._extents if e > 0])

    def _accumulate(self, extents: Iterable[int]) -> int:
        return reduce(mul, extents, 1)
