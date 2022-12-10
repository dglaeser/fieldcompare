"""Class to represent a sequence of field data (e.g. a time series)"""

from __future__ import annotations
from typing import Protocol, Iterator

from .protocols import FieldData


class FieldDataSequenceSource(Protocol):
    """Providess access to the data of the steps of the sequence"""

    def reset(self) -> None:
        """Go back to the first step in the sequence"""
        ...

    def step(self) -> bool:
        """Move to the next step in the sequence and return true if succeeded"""
        ...

    def get(self) -> FieldData:
        """Return the data of this step"""
        ...


class FieldDataSequence:
    """A sequence over several fields (e.g. a time series)"""
    def __init__(self, source: FieldDataSequenceSource) -> None:
        self._source = source

    def __iter__(self) -> Iterator[FieldData]:
        """Return an iterator over all steps in the sequence"""
        self._source.reset()
        yield self._source.get()
        while self._source.step():
            yield self._source.get()
        return
