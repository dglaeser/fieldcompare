"""Defines the interfaces used by the fieldcompare.mesh module"""
from typing import Protocol, Iterable, Tuple, runtime_checkable
from .._array import Array
from ..protocols import FieldData, Field


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
