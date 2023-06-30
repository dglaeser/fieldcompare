# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Class to represent permuted computational meshes"""

from __future__ import annotations
from typing import Iterable
from numbers import Integral

from .._numpy_utils import Array, max_element, make_array, make_uninitialized_array
from ..predicates import PredicateResult
from ..protocols import DynamicTolerance

from ._cell_type import CellType
from ._mesh_equal import mesh_equal
from . import protocols


class PermutedMesh:
    """
    Represents a computational mesh, permuted by the given index maps.

    Args:
        mesh: The unpermuted mesh
        point_permutation: The permutation (index map) to be applied on the points.
        cell_permutations: The permutations (index maps) to be applied to the cell connectivities.
                           For each cell type of the grid, a separate permutation is specified.
    """

    def __init__(
        self,
        mesh: protocols.Mesh,
        point_permutation: Array | None = None,
        cell_permutations: dict[CellType, Array] | None = None,
    ) -> None:
        self._mesh = mesh
        self._point_permutation = point_permutation
        self._cell_permutations = cell_permutations
        self._inverse_point_permutation = self._make_inverse_point_permutation()
        self._abs_tol: float | None = None
        self._rel_tol: float | None = None

    @property
    def absolute_tolerance(self) -> float:
        """Return the absolute tolerance defined for equality checks against other meshes."""
        return self._abs_tol if self._abs_tol is not None else self._mesh.absolute_tolerance

    @property
    def relative_tolerance(self) -> float:
        """Return the relative tolerance defined for equality checks against other meshes."""
        return self._rel_tol if self._rel_tol is not None else self._mesh.relative_tolerance

    @property
    def points(self) -> Array:
        """Return the points of this mesh."""
        if self._point_permutation is not None:
            return self._mesh.points[self._point_permutation]
        return self._mesh.points

    @property
    def cell_types(self) -> Iterable[CellType]:
        """Return the cell types present in this mesh."""
        return self._mesh.cell_types

    def connectivity(self, cell_type: CellType) -> Array:
        """
        Return the corner indices array for the cells of the given type.

        Args:
            cell_type: The cell type for which to return the connectivity.
        """
        corner_indices = self._mesh.connectivity(cell_type)
        if self._inverse_point_permutation is not None:
            corner_indices = self._inverse_point_permutation[corner_indices]
        return self.transform_cell_data(cell_type, corner_indices)

    def transform_point_data(self, data: Array) -> Array:
        """
        Transform the given point data values.

        Args:
            data: The point data to be transformed.
        """
        if self._point_permutation is not None:
            return data[self._point_permutation]
        return data

    def transform_cell_data(self, cell_type: CellType, data: Array) -> Array:
        """
        Transform the given cell data values.

        Args:
            cell_type: The cell type for which the given data is defined.
            data: The data to be transformed.
        """
        if self._cell_permutations is not None:
            return data[self._cell_permutations[cell_type]]
        return data

    def equals(self, other: protocols.Mesh) -> PredicateResult:
        """
        Check whether this mesh is equal to the given one.

        Args:
            other: mesh against with to check equality.
        """
        return mesh_equal(
            self,
            other,
            abs_tol=self.absolute_tolerance,
            rel_tol=self.relative_tolerance,
        )

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
        result = tol(self._mesh.points, self._mesh.points) if isinstance(tol, DynamicTolerance) else tol
        assert isinstance(result, float)
        return result

    def _make_inverse_point_permutation(self) -> Array | None:
        if self._point_permutation is None:
            return None
        index_map = self._point_permutation
        max_index = max_element(index_map)
        assert isinstance(max_index, Integral)
        inverse = make_uninitialized_array(max_index + 1, dtype=int)
        inverse[index_map] = make_array(list(range(len(index_map))))
        return inverse
