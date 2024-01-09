# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Class to represent structured computational meshes"""

from __future__ import annotations
from typing import Iterable, Tuple, List
from itertools import accumulate, product
from functools import reduce
from operator import mul

from ..predicates import FuzzyEquality, PredicateResult
from ..protocols import DynamicTolerance
from .._numpy_utils import Array, ArrayLike, as_array, max_abs_value, make_zeros, make_array

from ._mesh import default_mesh_relative_tolerance
from ._mesh_equal import mesh_equal
from ._cell_type import CellType, CellTypes

from . import protocols


class _StructuredMeshBase:
    def __init__(self, extents: Tuple[int, int, int], max_coordinate: float) -> None:
        if len(extents) != 3:  # noqa: PLR2004
            raise ValueError(f"Expected three-dimensional extents tuple, got {extents}")

        self._extents = extents
        self._dimension = len(self._nonzero_extents())
        self._rel_tol = default_mesh_relative_tolerance()
        self._abs_tol = max_coordinate * default_mesh_relative_tolerance()

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

    def connectivity(self, cell_type: CellType) -> Array:
        """
        Return the corner indices array for the cells of the given type.

        Args:
            cell_type: The cell type for which to return the connectivity.
        """
        if cell_type != self._cell_type():
            return make_array([])

        extents = self._nonzero_extents()
        offsets = list(accumulate((e + 1 for e in extents), mul))[:-1]
        num_cell_corners = pow(self._dimension, 2)

        def _get_p0(ituple) -> int:
            return sum(ituple[i] * (offsets[i - 1] if i > 0 else 1) for i in range(len(ituple)))

        connectivity = make_zeros(shape=(self._num_cells(), num_cell_corners), dtype=int)
        if self._dimension == 1:  # noqa: PLR2004
            for cell_idx, ituple in enumerate(product(*list(range(e) for e in extents))):
                p0 = _get_p0(ituple)
                connectivity[cell_idx] = [p0, p0 + 1]
        elif self._dimension == 2:  # noqa: PLR2004
            for cell_idx, ituple in enumerate(product(*list(range(e) for e in extents))):
                p0 = _get_p0(ituple)
                p2 = p0 + offsets[0]
                connectivity[cell_idx] = [p0, p0 + 1, p2 + 1, p2]
        elif self._dimension == 3:  # noqa: PLR2004
            for cell_idx, ituple in enumerate(product(*list(range(e) for e in extents))):
                p0 = _get_p0(ituple)
                p2 = p0 + offsets[0]
                p5 = p0 + offsets[1]
                p7 = p5 + offsets[0]
                connectivity[cell_idx] = [p0, p0 + 1, p2 + 1, p2, p5, p5 + 1, p7 + 1, p7]

        return connectivity

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
        self._rel_tol = self._rel_tol if rel_tol is None else self._compute_tolerance_from(rel_tol)
        self._abs_tol = self._abs_tol if abs_tol is None else self._compute_tolerance_from(abs_tol)

    def _compute_tolerance_from(self, tol: float | DynamicTolerance) -> float:
        raise RuntimeError("Mesh implementation does not implement _compute_tolerance_from()")

    def _cell_type(self) -> CellType:
        raise RuntimeError("Mesh implementation does not implement _cell_type()")

    def _num_cells(self) -> int:
        return self._accumulate(self._nonzero_extents())

    def _nonzero_extents(self) -> List[int]:
        return list([e for e in self._extents if e > 0])

    def _accumulate(self, extents: Iterable[int]) -> int:
        return reduce(mul, extents, 1)


class StructuredMesh(_StructuredMeshBase):
    """
    Represents a structured computational mesh.

    Args:
        extents: The number of cells per coordinate direction
        points: The points of the structured mesh
    """

    def __init__(self, extents: Tuple[int, int, int], points: ArrayLike) -> None:
        self._points = as_array(points)
        super().__init__(extents, max_coordinate=max_abs_value(self._points))

        expected_num_points = self._accumulate(map(lambda e: e + 1, extents))
        if len(self._points) != expected_num_points:
            raise ValueError(
                f"Number of points, computed from the given extents ({extents}), "
                f"is {expected_num_points}, but the given point array has length {len(self._points)}"
            )

    @property
    def points(self) -> Array:
        """Return the points of this mesh."""
        return self._points

    @property
    def cell_types(self) -> Iterable[CellType]:
        """Return the cell types present in this mesh."""
        return [[CellTypes.line, CellTypes.quad, CellTypes.hexahedron][self._dimension - 1]]

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

    def _compute_tolerance_from(self, tol: float | DynamicTolerance) -> float:
        result = tol(self._points, self._points) if isinstance(tol, DynamicTolerance) else tol
        assert isinstance(result, float)
        return result

    def _cell_type(self) -> CellType:
        return CellTypes.quad
