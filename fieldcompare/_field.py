"""Class that represents a field of values"""

from dataclasses import dataclass
from ._array import Array


@dataclass
class Field:
    """Represents a field with a name and an array of values"""
    name: str
    values: Array
