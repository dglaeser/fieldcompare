"""Definitions of the interfaces used by fieldcompare"""

from __future__ import annotations
from typing import Protocol, Callable, Iterator, Any, runtime_checkable
from ._numpy_utils import Array, ArrayTolerance


@runtime_checkable
class ToleranceEstimator(Protocol):
    """Interface for estimators of tolerances from array values."""

    def __call__(self, first: Array, second: Array) -> ArrayTolerance:
        ...


@runtime_checkable
class PredicateResult(Protocol):
    """Return value from predicate functions."""

    def __bool__(self) -> bool:
        """Return true if the predicate evaluated to true."""
        ...

    @property
    def report(self) -> str:
        """Return a report of the predicate evaluation."""
        ...


Predicate = Callable[[Any, Any], PredicateResult]


@runtime_checkable
class Domain(Protocol):
    """Represents a domain on which fields are defined."""

    def equals(self, other: Domain) -> PredicateResult:
        """
        Check if this domain is equal to the given one.

        Args:
            other: Domain against which to check for equality.
        """
        ...


@runtime_checkable
class Field(Protocol):
    """Represents a single field."""

    @property
    def name(self) -> str:
        """Return the name of the field."""
        ...

    @property
    def values(self) -> Array:
        """Return the field values."""
        ...


@runtime_checkable
class FieldData(Protocol):
    """Contains the fields defined on a domain."""

    @property
    def domain(self) -> Any:
        """Return the domain these fields are defined on."""
        ...

    def __iter__(self) -> Iterator[Field]:
        """Return an iterator over the contained fields."""
        ...


@runtime_checkable
class FieldDataSequence(Protocol):
    """Represents a sequence of fields, for instance, a time series."""

    @property
    def number_of_steps(self) -> int:
        """Return the number of steps in the sequence."""
        ...

    def __iter__(self) -> Iterator[FieldData]:
        """Return an iterator over the field data of the sequence."""
        ...
