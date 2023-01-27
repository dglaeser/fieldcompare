# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Classes to represent fields on computational meshes."""

from __future__ import annotations
from itertools import chain
from typing import Iterator, Iterable, Dict, List, Tuple, Callable, Protocol, runtime_checkable

from .._numpy_utils import Array, as_array
from .._field import Field
from ._cell_type import CellType

from . import protocols
from .. import protocols as fc_protocols
from .._format import add_annotation, split_annotation


def make_cell_type_field_name(cell_type: CellType, field_name: str) -> str:
    """Append the cell type suffix to the field name."""
    return add_annotation(field_name, f"{cell_type.name}")


def remove_cell_type_suffix(cell_type: CellType, field_name_with_suffix: str) -> str:
    """Remove the cell type suffix from the given field name."""
    name, annotation = split_annotation(field_name_with_suffix)
    assert cell_type.name in annotation
    return name


class MeshFields(fc_protocols.FieldData):
    """
    Represents field data on a computational mesh.

    Args:
        mesh: The underlying mesh.
        point_data: The fields defined on the points of the mesh.
        cell_data: The field data defined on the mesh cells. The field values
                   have to be specified as a list of arrays, where each array contains
                   the values for the cells of a particular cell type. The ordering of the
                   arrays has to follow the order of the cell types as exposed by the mesh.
    """

    def __init__(
        self, mesh: protocols.Mesh, point_data: Dict[str, Array] = {}, cell_data: Dict[str, List[Array]] = {}
    ) -> None:
        self._mesh = mesh
        self._point_data = {name: self._make_point_values(data) for name, data in point_data.items()}
        self._cell_data = {
            name: {
                cell_type: self._make_cell_values(cell_type, cell_values)
                for cell_type, cell_values in zip(mesh.cell_types, cell_data[name])
            }
            for name in cell_data
        }

    @property
    def domain(self) -> protocols.Mesh:
        """Return the mesh on which these fields are defined."""
        return self._mesh

    def __iter__(self) -> Iterator[Field]:
        """Return an iterator over the contained fields."""
        return chain(self.point_fields, self.cell_fields)

    @property
    def point_fields(self) -> Iterable[Field]:
        """Return an range over the contained point fields."""
        return (Field(name, values) for name, values in self._point_data.items())

    @property
    def cell_fields(self) -> Iterable[Field]:
        """Return an range over the contained cell fields."""
        return (_tup[0] for _tup in self.cell_fields_types)

    @property
    def cell_fields_types(self) -> Iterable[Tuple[Field, CellType]]:
        """Return a range over cell fields + associated cell type."""
        return (
            (Field(make_cell_type_field_name(cell_type, name), self._cell_data[name][cell_type]), cell_type)
            for cell_type in self._mesh.cell_types
            for name in self._cell_data
        )

    def _make_point_values(self, values: Array) -> Array:
        values = as_array(values)
        if values.shape[0] != self._mesh.points.shape[0]:
            raise ValueError("Length of the given point data does " "not match number of mesh points")
        return values

    def _make_cell_values(self, cell_type: CellType, values: Array) -> Array:
        values = as_array(values)
        if values.shape[0] != self._mesh.connectivity(cell_type).shape[0]:
            raise ValueError(f"Length of the given cell data for '{cell_type}' " "does not match the number of cells.")
        return values


class TransformedMeshFields(fc_protocols.FieldData):
    """
    Exposes field data on transformed meshes.

    Args:
        field_data: The untransformed mesh fields.
        transformation: The mesh transformation to be applied.
    """

    @runtime_checkable
    class TransformedMesh(protocols.Mesh, Protocol):
        def transform_point_data(self, data: Array) -> Array:
            """
            Return the transformed point data.

            Args:
                data: The point data array to be transformed.
            """
            ...

        def transform_cell_data(self, cell_type: CellType, data: Array) -> Array:
            """
            Return the transformed cell data.

            Args:
                cell_type: The cell type for which the data is defined.
                data: The data array to be transformed.
            """
            ...

    def __init__(
        self, field_data: protocols.MeshFields, transformation: Callable[[protocols.Mesh], TransformedMesh]
    ) -> None:
        self._field_data = field_data
        self._mesh = transformation(self._field_data.domain)
        self._mesh.set_tolerances(
            abs_tol=self._field_data.domain.absolute_tolerance, rel_tol=self._field_data.domain.relative_tolerance
        )

    @property
    def domain(self) -> TransformedMesh:
        """Return the mesh on which these fields are defined"""
        return self._mesh

    def __iter__(self) -> Iterator[fc_protocols.Field]:
        """Return an iterator over the contained fields"""
        return chain(self.point_fields, self.cell_fields)

    @property
    def point_fields(self) -> Iterable[fc_protocols.Field]:
        """Return a range over the contained point fields"""
        return (self._get_permuted_point_field(_field) for _field in self._field_data.point_fields)

    @property
    def cell_fields(self) -> Iterable[Field]:
        """Return a range over the contained cell fields"""
        return (_tup[0] for _tup in self.cell_fields_types)

    @property
    def cell_fields_types(self) -> Iterable[Tuple[Field, CellType]]:
        """Return a range over cell field / cell type tuples"""
        return (
            (self._get_permuted_cell_field(cell_type, field), cell_type)
            for field, cell_type in self._field_data.cell_fields_types
        )

    def _get_permuted_point_field(self, field: fc_protocols.Field) -> fc_protocols.Field:
        return Field(field.name, self._mesh.transform_point_data(field.values))

    def _get_permuted_cell_field(self, cell_type: CellType, field: fc_protocols.Field) -> Field:
        return Field(field.name, self._mesh.transform_cell_data(cell_type, field.values))
