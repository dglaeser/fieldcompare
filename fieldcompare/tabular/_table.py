"""Domain implementation for tabular data"""

from __future__ import annotations
from typing import Optional

from .._array import Array
from ..predicates import PredicateResult


class Table:
    def __init__(self,
                 num_rows: Optional[int] = None,
                 idx_map: Optional[Array] = None) -> None:
        self._idx_map = idx_map
        if self._idx_map is not None:
            self._num_rows = len(self._idx_map)
            if num_rows is not None and num_rows != self._num_rows:
                raise ValueError("Given number of rows does not match the length of the index map")
        elif num_rows is not None:
            self._num_rows = num_rows
        else:
            raise ValueError("Either the number of rows or an index map have to be specified")

    @property
    def number_of_rows(self) -> int:
        """Return the length of the table"""
        return self._num_rows

    @property
    def indices(self) -> Optional[Array]:
        """Return the index map used for filtering the data columns"""
        return self._idx_map

    def equals(self, other: Table) -> PredicateResult:
        """Check if this table is equal to the given one (true if number of rows are equal)"""
        if self.number_of_rows != other.number_of_rows:
            return PredicateResult(False, "Differing number of rows")
        return PredicateResult(True)
