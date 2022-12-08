"""Defines the interfaces used by fieldcompare"""

from __future__ import annotations
from typing import Protocol, Optional, Iterator, Any
from ._array import Array


class Field(Protocol):
    """Represents a single field consisting of a name and field values"""

    @property
    def name(self) -> str:
        """Return the name of the field"""
        ...

    @property
    def values(self) -> Array:
        """Return the field values"""
        ...


class PredicateResult(Protocol):
    """Return value from predicate functions"""
    def __bool__(self) -> bool:
        """Return true if the predicate evaluated to true"""
        ...

    def report(self, verbosity_level: Optional[int] = None) -> str:
        """Return a report of the predicate evaluation"""
        ...


class Domain(Protocol):
    """Represents a domain on which fields are defined"""
    def equals(self, other: Domain) -> PredicateResult:
        """Check if this domain is equal to the given domain"""
        ...


class FieldData(Protocol):
    """Contains the fields defined on a domain"""

    @property
    def domain(self) -> Any:
        """Return the domain these fields are defined on"""
        ...

    def __iter__(self) -> Iterator[Field]:
        """Return an iterator over the contained fields"""
        ...

    def permuted(self, permutation) -> FieldData:
        """Return this field data permuted by the given permutation"""
        ...
