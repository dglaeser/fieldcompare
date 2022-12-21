"""Class to represent a sequence of field data (e.g. a time series)"""

from __future__ import annotations
from typing import Protocol, Iterator, runtime_checkable

from .protocols import FieldData


class FieldDataSequence:
    """Represents a sequence of :class:`.FieldData` (e.g. a time series)"""

    @runtime_checkable
    class Source(Protocol):
        """Interface for sources, providing access to the data of the steps of the sequence"""

        def reset(self) -> None:
            """Go back to the first step in the sequence"""
            ...

        def step(self) -> bool:
            """Move to the next step in the sequence and return true if succeeded"""
            ...

        def get(self) -> FieldData:
            """Return the data of this step"""
            ...

        @property
        def number_of_steps(self) -> int:
            """Return the number of steps in the sequence"""
            ...

    def __init__(self, source: Source) -> None:
        """Construct the sequence from the given source"""
        self._source = source

    def __iter__(self) -> Iterator:
        """Return an iterator over all steps in the sequence"""
        self._source.reset()
        yield self._source.get()
        while self._source.step():
            yield self._source.get()

    @property
    def number_of_steps(self) -> int:
        """Return the number of steps in the sequence"""
        return self._source.number_of_steps
