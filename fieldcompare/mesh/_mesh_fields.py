"""Classes to represent fields on computational meshes"""

from __future__ import annotations
from itertools import chain
from typing import (
    Iterator, Iterable,
    Dict, List, Tuple,
    Union, Callable
)

from .._numpy_utils import Array, as_array
from .._field import Field
from ..protocols import FieldData

from ._cell_type import CellType
from .protocols import Mesh, TransformedMesh


def _cell_type_suffix(cell_type: CellType) -> str:
    return f" ({cell_type.name})"


def make_cell_type_field_name(cell_type: CellType, field_name: str) -> str:
    """Append the cell type suffix to the field name"""
    return f"{field_name}{_cell_type_suffix(cell_type)}"


def remove_cell_type_suffix(cell_type: CellType, field_name_with_suffix: str) -> str:
    """Remove the cell type suffix from the given field name"""
    return field_name_with_suffix.rstrip(_cell_type_suffix(cell_type))


class MeshFields(FieldData):
    """Class to represent field data on a computational mesh"""
    def __init__(self,
                 mesh: Mesh,
                 point_data: Dict[str, Array] = {},
                 cell_data: Dict[str, List[Array]] = {}) -> None:
        """Construct mesh fields from the given mesh and point/cell data

        Args:
            mesh: The mesh
            point_data: The field data defined on the mesh points.
            cell_data: The field data defined on the mesh cells. The field values
                have to be specified as a list of arrays, where each array contains
                the values for the cells of a particular cell type. The ordering of the
                arrays has to follow the order of the cell types as exposed by the mesh.
        """
        self._mesh = mesh
        self._point_data = {
            name: self._make_point_values(data)
            for name, data in point_data.items()
        }
        self._cell_data = {
            name: {
                cell_type: self._make_cell_values(cell_type, cell_values)
                for cell_type, cell_values in zip(mesh.cell_types, cell_data[name])
            } for name in cell_data
        }

    @property
    def domain(self) -> Mesh:
        """Return the mesh on which these fields are defined"""
        return self._mesh

    def __iter__(self) -> Iterator[Field]:
        """Return an iterator over the contained fields"""
        return chain(self.point_fields, self.cell_fields)

    @property
    def point_fields(self) -> Iterable[Field]:
        """Return an range over the contained point fields"""
        return (Field(name, values) for name, values in self._point_data.items())

    @property
    def cell_fields(self) -> Iterable[Field]:
        """Return an range over the contained cell fields"""
        return (_tup[0] for _tup in self.cell_fields_types)

    @property
    def cell_fields_types(self) -> Iterable[Tuple[Field, CellType]]:
        """Return a range over cell fields + associated cell type"""
        return (
            (
                Field(
                    make_cell_type_field_name(cell_type, name),
                    self._cell_data[name][cell_type]
                ),
                cell_type
            )
            for cell_type in self._mesh.cell_types
            for name in self._cell_data
        )

    def transformed(self, transformation: Callable[[Mesh], TransformedMesh]) -> TransformedMeshFields:
        """Return the fields transformed by the given transformation"""
        return TransformedMeshFields(self, transformation)

    def _make_point_values(self, values: Array) -> Array:
        values = as_array(values)
        if values.shape[0] != self._mesh.points.shape[0]:
            raise ValueError(
                "Length of the given point data does "
                "not match number of mesh points")
        return values

    def _make_cell_values(self, cell_type: CellType, values: Array) -> Array:
        values = as_array(values)
        if values.shape[0] != self._mesh.connectivity(cell_type).shape[0]:
            raise ValueError(
                f"Length of the given cell data for '{cell_type}' "
                "does not match the number of cells."
            )
        return values


class TransformedMeshFields(FieldData):
    """Exposes field data on transformed meshes"""
    def __init__(self,
                 field_data: Union[MeshFields, TransformedMeshFields],
                 permutation: Callable[[Mesh], TransformedMesh]) -> None:
        self._field_data = field_data
        self._mesh = permutation(self._field_data.domain)

    @property
    def domain(self) -> TransformedMesh:
        """Return the mesh on which these fields are defined"""
        return self._mesh

    def __iter__(self) -> Iterator[Field]:
        """Return an iterator over the contained fields"""
        return chain(self.point_fields, self.cell_fields)

    @property
    def point_fields(self) -> Iterable[Field]:
        """Return a range over the contained point fields"""
        return (
            self._get_permuted_point_field(_field)
            for _field in self._field_data.point_fields
        )

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

    def transformed(self, transformation: Callable[[Mesh], TransformedMesh]) -> TransformedMeshFields:
        """Return the fields transformed by the given transformation"""
        return TransformedMeshFields(self, transformation)

    def _get_permuted_point_field(self, field: Field) -> Field:
        return Field(
            field.name,
            self._mesh.transform_point_data(field.values)
        )

    def _get_permuted_cell_field(self, cell_type: CellType, field: Field) -> Field:
        return Field(
            field.name,
            self._mesh.transform_cell_data(cell_type, field.values)
        )
