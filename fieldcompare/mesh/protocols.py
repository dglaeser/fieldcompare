"""Defines the interfaces used by the fieldcompare.mesh module"""

from __future__ import annotations
from typing import Protocol, Iterable, Tuple, Optional, Callable, runtime_checkable

from ..protocols import FieldData, Field, PredicateResult
from .._array import Array


@runtime_checkable
class Mesh(Protocol):
    """Represents a computational mesh"""

    @property
    def points(self) -> Array:
        """Return the points of this mesh"""
        ...

    @property
    def cell_types(self) -> Iterable[str]:
        """Return the cell types present in this mesh"""
        ...

    def connectivity(self, cell_type: str) -> Array:
        """Return the corner indices array for the cells of the given type"""
        ...

    def equals(self, other: Mesh) -> PredicateResult:
        """Check if this mesh is equal to the given one"""
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
        """Set the tolerances used for equality checks against other meshes"""
        ...


@runtime_checkable
class MeshFields(FieldData, Protocol):
    """Represents fields defined on a computational mesh"""
    @property
    def domain(self) -> Mesh:
        """Return the mesh on which the fields are defined"""
        ...

    @property
    def point_fields(self) -> Iterable[Field]:
        """Return an range over the contained point fields"""
        ...

    @property
    def cell_fields(self) -> Iterable[Field]:
        """Return an range over the contained cell fields"""
        ...

    @property
    def cell_fields_types(self) -> Iterable[Tuple[Field, str]]:
        """Return a range over cell fields + associated cell type"""
        ...

    def permuted(self, permutation: Callable[[Mesh], Mesh]) -> MeshFields:
        """Permute the mesh fields with the given mesh permutation"""
        ...
