"""Defines the interfaces used by the fieldcompare.mesh module"""
from typing import Protocol, Iterable, runtime_checkable
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
