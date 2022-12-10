"""Class to represent a computational mesh"""
from __future__ import annotations
from itertools import chain
from typing import (
    Iterator, Iterable,
    Dict, List, Tuple,
    Union, Callable
)

from .._array import Array, as_array
from .._field import Field

from .protocols import Mesh
from ._permuted_mesh import PermutedMesh


def _cell_type_suffix(cell_type: str) -> str:
    return f" ({cell_type})"


def make_cell_type_field_name(cell_type: str, field_name: str) -> str:
    """Append the cell type suffix to the field name"""
    return f"{field_name}{_cell_type_suffix(cell_type)}"


def remove_cell_type_suffix(cell_type: str, field_name_with_suffix: str) -> str:
    """Remove the cell type suffix from the given field name"""
    return field_name_with_suffix.rstrip(_cell_type_suffix(cell_type))


class MeshFields:
    """Class to represent field data on a computational mesh"""
    def __init__(self,
                 mesh: Mesh,
                 point_data: Dict[str, Array] = {},
                 cell_data: Dict[str, List[Array]] = {}) -> None:
        self._mesh = mesh
        self._point_data = {
            name: as_array(data)
            for name, data in point_data.items()
        }
        self._cell_data = {
            name: {
                cell_type: as_array(connectivity)
                for cell_type, connectivity in zip(mesh.cell_types, cell_data[name])
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
    def cell_fields_types(self) -> Iterable[Tuple[Field, str]]:
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

    def permuted(self, permutation: Callable[[Mesh], PermutedMesh]) -> PermutedMeshFields:
        """Return the fields as permuted by the given permutation"""
        return PermutedMeshFields(self, permutation)


class PermutedMeshFields:
    """Exposes field data on permuted meshes"""
    def __init__(self,
                 field_data: Union[MeshFields, PermutedMeshFields],
                 permutation: Callable[[Mesh], PermutedMesh]) -> None:
        self._field_data = field_data
        self._mesh = permutation(self._field_data.domain)

    @property
    def domain(self) -> PermutedMesh:
        """Return the mesh on which these fields are defined"""
        return self._mesh

    def __iter__(self) -> Iterator[Field]:
        """Return an iterator over the contained fields"""
        return chain(self.point_fields, self.cell_fields)

    @property
    def point_fields(self) -> Iterable[Field]:
        """Return an iterator over the contained point fields"""
        return (
            Field(_field.name, self._mesh.permute_point_data(_field.values))
            for _field in self._field_data.point_fields
        )

    @property
    def cell_fields(self) -> Iterable[Field]:
        """Return an iterator over the contained cell fields"""
        return (_tup[0] for _tup in self.cell_fields_types)

    @property
    def cell_fields_types(self) -> Iterable[Tuple[Field, str]]:
        return (
            (self._get_permuted_cell_field(cell_type, field), cell_type)
            for field, cell_type in self._field_data.cell_fields_types
        )

    def permuted(self, permutation: Callable[[Mesh], PermutedMesh]) -> PermutedMeshFields:
        """Return the fields as permuted by the given permutation"""
        return PermutedMeshFields(self, permutation)

    def _get_permuted_cell_field(self, cell_type: str, field: Field) -> Field:
        return Field(
            field.name,
            self._mesh.permute_cell_data(cell_type, field.values)
        )
