# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""FieldData implementation for tabular data."""

from __future__ import annotations
from typing import Iterator, Dict, Callable

from numpy import nan

from .._field import Field
from .._numpy_utils import Array, make_array
from .._matching import find_matches_by_name
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

    def diff_to(self, other: TabularFields) -> TabularFields:
        """Return the tabular data that contains the difference to the given tabular data"""
        return _subtract(other, self)


def transform(fields: TabularFields, transformation: Callable[[Table], Table]) -> TabularFields:
    """
    Return the given fields transformed by the given transformation.

    Args:
        transformation: The transformation to be applied.
    """
    return TabularFields(domain=transformation(fields.domain), fields={field.name: field.values for field in fields})


def _subtract(fields1: TabularFields, fields2: TabularFields) -> TabularFields:
    matches = find_matches_by_name(source=fields1, reference=fields2)
    matching_fields = [match[0].name for match in matches.matches]
    orphans1 = [f.name for f in matches.orphans_in_source]
    orphans2 = [f.name for f in matches.orphans_in_reference]

    field_map_1 = {f.name: f.values for f in fields1}
    field_map_2 = {f.name: f.values for f in fields2}
    diff_domain = Table(num_rows=max(fields1.domain.number_of_rows, fields2.domain.number_of_rows))
    diff_fields = {
        n: make_array([nan for _ in range(diff_domain.number_of_rows)]) for n in matching_fields + orphans1 + orphans2
    }
    for fname in matching_fields:
        for i, (a, b) in enumerate(zip(field_map_1[fname], field_map_2[fname])):
            diff_fields[fname][i] = a - b
    return TabularFields(domain=diff_domain, fields=diff_fields)
