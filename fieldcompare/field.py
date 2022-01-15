"""Class that represents a field of values"""

from abc import ABC, abstractmethod
from typing import Iterable, Collection

from fieldcompare._common import Array
from fieldcompare._common import make_array

class FieldInterface(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this field"""

    @property
    @abstractmethod
    def values(self) -> Collection:
        """Return the underlying field values"""


class Field(FieldInterface):
    """Class to represents a field of values"""
    def __init__(self, name: str, values: Iterable):
        self._name = name
        self._values = make_array(values) if not isinstance(values, Array) else values

    @property
    def name(self) -> str:
        """Return the name of this field"""
        return self._name

    @property
    def values(self) -> Array:
        """Return the field values"""
        return self._values
