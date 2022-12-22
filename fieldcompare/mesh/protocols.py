"""Defines the interfaces used by the fieldcompare.mesh module"""

from __future__ import annotations
from typing import Protocol, Iterable, Tuple, Optional, runtime_checkable

from ..protocols import FieldData, Field, PredicateResult
from .._numpy_utils import Array

from ._cell_type import CellType


@runtime_checkable
class Mesh(Protocol):
    """Represents a computational mesh"""

    @property
    def points(self) -> Array:
        """Return the points of this mesh"""
        ...

    @property
    def cell_types(self) -> Iterable[CellType]:
        """Return the cell types present in this mesh"""
        ...

    def connectivity(self, cell_type: CellType) -> Array:
        """
        Return the corner indices array for the cells of the given type.

        Args:
            cell_type: The cell type for which to return the connectivity.
        """
        ...

    def equals(self, other: Mesh) -> PredicateResult:
        """
        Check whether this mesh is equal to the given one.

        Args:
            other: mesh against with to check equality.
        """
        ...

    @property
    def absolute_tolerance(self) -> float:
        """Return the absolute tolerance used in equality checks against other meshes"""
        ...

    @property
    def relative_tolerance(self) -> float:
        """Return the relative tolerance used in equality checks against other meshes"""
        ...

    def set_tolerances(self, abs_tol: Optional[float] = None, rel_tol: Optional[float] = None) -> None:
        """
        Set the tolerances to be used for equality checks against other meshes.

        Args:
            abs_tol: Absolute tolerance to use.
            rel_tol: Relative tolerance to use.
        """
        ...


@runtime_checkable
class TransformedMesh(Mesh, Protocol):
    def transform_point_data(self, data: Array) -> Array:
        """
        Return the transformed point data.

        Args:
            data: The point data array to be transformed.
        """
        ...

    def transform_cell_data(self, cell_type: CellType, data: Array) -> Array:
        """
        Return the transformed cell data.

        Args:
            cell_type: The cell type for which the data is defined.
            data: The data array to be transformed.
        """
        ...


@runtime_checkable
class MeshFields(FieldData, Protocol):
    """Represents fields defined on a computational mesh."""

    @property
    def domain(self) -> Mesh:
        """Return the mesh on which the fields are defined."""
        ...

    @property
    def point_fields(self) -> Iterable[Field]:
        """Return an range over the contained point fields."""
        ...

    @property
    def cell_fields(self) -> Iterable[Field]:
        """Return an range over the contained cell fields."""
        ...

    @property
    def cell_fields_types(self) -> Iterable[Tuple[Field, CellType]]:
        """Return a range over cell fields + associated cell type."""
        ...
