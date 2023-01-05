"""FieldData implementation for tabular data."""

from __future__ import annotations
from typing import Iterator, Dict, Callable

from .._field import Field
from .._numpy_utils import Array
from ._table import Table
from ..protocols import FieldData


class TabularFields(FieldData):
    """
    Represents tabulare field data.

    Args:
        domain: The table on which the data is defined.
        fields: The fields defined on the given table.
    """

    def __init__(self, domain: Table, fields: Dict[str, Array]) -> None:
        self._domain = domain
        self._fields = fields
        assert all(len(values) == domain.number_of_rows for values in fields.values())

    @property
    def domain(self) -> Table:
        """Return the table on which these fields are defined."""
        return self._domain

    def __iter__(self) -> Iterator[Field]:
        """Return the fields contained in this table."""

        def _mapped_values(values: Array) -> Array:
            if self._domain.indices is not None:
                return values[self._domain.indices]
            return values

        return (Field(name, _mapped_values(values)) for name, values in self._fields.items())


def transform(self, transformation: Callable[[Table], Table]) -> TabularFields:
    """
    Return these fields transformed by the given transformation.

    Args:
        transformation: The transformation to be applied.
    """
    return TabularFields(domain=transformation(self.domain), fields=self._fields)
