"""Class that represents a field of values"""

from typing import Protocol
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


@dataclass
class Field:
    name: str
    values: Array
