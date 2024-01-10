# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Class to represent structured computational meshes"""

from __future__ import annotations
from typing import Iterable, Tuple, List
from itertools import accumulate, product
from functools import reduce
from operator import mul
from numpy import flip

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
    def cell_types(self) -> Iterable[CellType]:
        """Return the cell types present in this mesh."""
        return [self._cell_type()]

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
        return self._compute_number_of_entities(self._nonzero_extents())

    def _nonzero_extents(self) -> List[int]:
        return list([e for e in self._extents if e > 0])

    def _compute_number_of_entities(self, extents: Iterable[int]) -> int:
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

        expected_num_points = self._compute_number_of_entities(map(lambda e: e + 1, extents))
        if len(self._points) != expected_num_points:
            raise ValueError(
                f"Number of points, computed from the given extents ({extents}), "
                f"is {expected_num_points}, but the given point array has length {len(self._points)}"
            )

    @property
    def points(self) -> Array:
        """Return the points of this mesh."""
        return self._points

    def equals(self, other: protocols.Mesh) -> PredicateResult:
        """
        Check whether this mesh is equal to the given one.

        Args:
            other: mesh against with to check equality.
        """
        if not isinstance(other, StructuredMesh):
            return mesh_equal(self, other)

        basic_check = _test_basic_grid_equality(self, other)
        if not basic_check:
            return basic_check

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
        return [CellTypes.line, CellTypes.quad, CellTypes.hexahedron][self._dimension - 1]


class RectilinearMesh(_StructuredMeshBase):
    """
    Represents a rectilinear computational mesh.

    Args:
        extents: The number of cells per coordinate direction
        ordinates: The ordinates of the points per coordinate direction
    """

    def __init__(self, extents: Tuple[int, int, int], ordinates: Tuple[ArrayLike, ArrayLike, ArrayLike]) -> None:
        self._points: Array | None = None
        self._ordinates = [as_array(ords) for ords in ordinates]
        self._ordinates = [arr if len(arr) > 0 else make_array([0.0]) for arr in self._ordinates]
        super().__init__(extents, max_coordinate=max(max_abs_value(o) for o in self._ordinates))

        self._num_points = self._compute_number_of_entities(map(lambda c: max(len(c), 1), self._ordinates))
        expected_num_points = self._compute_number_of_entities(map(lambda e: e + 1, extents))
        if self._num_points != expected_num_points:
            raise ValueError(
                f"Number of points, computed from the given extents ({extents}), "
                f"is {expected_num_points}, but the given ordinates yield {self._num_points}"
            )

    @property
    def points(self) -> Array:
        """Return the points of this mesh."""
        if self._points is None:
            self._points = make_zeros((self._num_points, 3))
            # go over directions from 3 to 0 to have points ordered as follows:
            # ([x0, y0, z0], [x1, y0, z0], ..., [xn, y0, z0], [x0, y1, z0], ...)
            for i, p in enumerate(product(*list(ords for ords in reversed(self._ordinates)))):
                self._points[i] = flip(p)
        return self._points

    def equals(self, other: protocols.Mesh) -> PredicateResult:
        """
        Check whether this mesh is equal to the given one.

        Args:
            other: mesh against with to check equality.
        """
        if not isinstance(other, RectilinearMesh):
            return mesh_equal(self, other)

        basic_check = _test_basic_grid_equality(self, other)
        if not basic_check:
            return basic_check

        for direction in range(self._dimension):
            if not FuzzyEquality(rel_tol=self.relative_tolerance, abs_tol=self.absolute_tolerance)(
                self._ordinates[direction], other._ordinates[direction]
            ):
                return PredicateResult(False, report=f"Differing ordinates in direction {direction}")
        return PredicateResult(True)

    def _compute_tolerance_from(self, tol: float | DynamicTolerance) -> float:
        points = self.points
        result = tol(points, points) if isinstance(tol, DynamicTolerance) else tol
        assert isinstance(result, float)
        return result

    def _cell_type(self) -> CellType:
        return [CellTypes.line, CellTypes.pixel, CellTypes.voxel][self._dimension - 1]


class ImageMesh(_StructuredMeshBase):
    """
    Represents an image mesh.

    Args:
        extents: The number of cells per coordinate direction
        origin: The origin (lower left corner) of the mesh
        spacing: The spacing in each coordinate direction
        basis: The basis vectors for each coordinate direction (optional)
    """

    def __init__(
        self,
        extents: Tuple[int, int, int],
        origin: Tuple[float, float, float],
        spacing: Tuple[float, float, float],
        basis: Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]] = (
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
        ),
    ) -> None:
        super().__init__(
            extents, max_coordinate=max(max(abs(origin[d]), abs(origin[d] + spacing[d] * extents[d])) for d in range(3))
        )

        self._origin = origin
        self._spacing = spacing
        self._basis = make_zeros((3, 3))
        for i, v in enumerate(basis):
            self._basis[i] = v

        self._points: Array | None = None
        self._num_points = self._compute_number_of_entities(map(lambda e: e + 1, self._extents))

    @property
    def points(self) -> Array:
        """Return the points of this mesh."""
        if self._points is None:
            self._points = make_zeros((self._num_points, 3))
            # go over directions from 3 to 0 to have points ordered as follows:
            # ([x0, y0, z0], [x1, y0, z0], ..., [xn, y0, z0], [x0, y1, z0], ...)
            for i, rev_ituple in enumerate(product(*list(range(e + 1) for e in reversed(self._extents)))):
                ituple = tuple(reversed(rev_ituple))
                self._points[i] = [
                    self._origin[0] + self._spacing[0] * float(ituple[0]),
                    self._origin[1] + self._spacing[1] * float(ituple[1]),
                    self._origin[2] + self._spacing[2] * float(ituple[2]),
                ]
        return self._points

    def equals(self, other: protocols.Mesh) -> PredicateResult:
        """
        Check whether this mesh is equal to the given one.

        Args:
            other: mesh against with to check equality.
        """
        if not isinstance(other, ImageMesh):
            return mesh_equal(self, other)

        basic_check = _test_basic_grid_equality(self, other)
        if not basic_check:
            return basic_check

        if not FuzzyEquality(rel_tol=self.relative_tolerance, abs_tol=self.absolute_tolerance)(
            self._origin, other._origin
        ):
            return PredicateResult(False, report=f"Different grid origin {self._origin} - {other._origin}")
        if not FuzzyEquality(rel_tol=self.relative_tolerance, abs_tol=self.absolute_tolerance)(
            self._spacing, other._spacing
        ):
            return PredicateResult(False, report=f"Different grid origin {self._spacing} - {other._spacing}")
        if not FuzzyEquality(rel_tol=self.relative_tolerance, abs_tol=self.absolute_tolerance)(
            self._basis, other._basis
        ):
            return PredicateResult(False, report=f"Different grid orientation {self._basis} - {other._basis}")
        return PredicateResult(True)

    def _compute_tolerance_from(self, tol: float | DynamicTolerance) -> float:
        points = self.points
        result = tol(points, points) if isinstance(tol, DynamicTolerance) else tol
        assert isinstance(result, float)
        return result

    def _cell_type(self) -> CellType:
        return [CellTypes.line, CellTypes.pixel, CellTypes.voxel][self._dimension - 1]


def _test_basic_grid_equality(grid1, grid2) -> PredicateResult:
    if grid1._extents != grid2._extents:
        return PredicateResult(False, report=f"Different structured grid extents: {grid1.extents} - {grid2.extents}")
    if grid1._dimension != grid2._dimension:
        return PredicateResult(False, report=f"Different grid dimension {grid1._dimension} - {grid2._dimension}")
    return PredicateResult(True)
