"""Class that represents a field of values"""

from abc import ABC, abstractmethod
from typing import Union, Sequence
from fieldcompare.array import Array, is_array, make_array


class FieldInterface(ABC):
    """Defines the interface of fields"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this field"""

    @property
    @abstractmethod
    def values(self) -> Array:
        """Return the underlying field values"""


class Field(FieldInterface):
    """Class to represents a field of values"""

    def __init__(self, name: str, values: Union[Array, Sequence]):
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
