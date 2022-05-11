"""Class that represents a field of values"""

from typing import Protocol, Iterable, Iterator
from dataclasses import dataclass
from .array import Array


class FieldInterface(Protocol):
    @property
    def name(self) -> str:
        """Return the name of this field"""
        ...

    @property
    def values(self) -> Array:
        """Return the underlying field values"""
        ...


class FieldContainer(Protocol):
    @property
    def field_names(self) -> Iterable[str]:
        """Return an iterable over the names over all contained fields"""
        ...

    def get(self, field_name: str) -> FieldInterface:
        """Return the field with the given name"""
        ...

    def __iter__(self) -> Iterator[FieldInterface]:
        """Return an iterator over the contained fields"""
        ...


@dataclass
class Field:
    name: str
    values: Array
