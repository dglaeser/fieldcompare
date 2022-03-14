"""Class that represents a field of values"""

from typing import Union, Sequence, Protocol
from .array import Array, is_array, make_array


class FieldInterface(Protocol):
    @property
    def name(self) -> str:
        """Return the name of this field"""
        ...

    @property
    def values(self) -> Array:
        """Return the underlying field values"""
        ...


class Field:
    def __init__(self, name: str, values: Union[Array, Sequence]) -> None:
        self._name = name
        self._values = _make_array(values)

    @property
    def name(self) -> str:
        """Return the name of this field"""
        return self._name

    @property
    def values(self) -> Array:
        """Return the field values"""
        return self._values


def _make_array(values) -> Array:
    return values if is_array(values) else make_array(values)
