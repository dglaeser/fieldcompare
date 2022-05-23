"""Wrapper around mesh field containers to represent meshes & fields with mapped indices"""

from typing import Protocol, Iterable, Iterator, Dict, Optional

from .._array import (
    Array,
    make_array,
    make_uninitialized_array,
    max_element
)

from .._field import Field
from ._mesh_fields import MeshFieldContainerInterface


class MapInterface(Protocol):
    def map(self, data: Array) -> Array:
        """Return the mapped the data array"""
        ...

    def as_indices(self) -> Array:
        """Return the indices representing this map"""
        ...


class _IdentityMap:
    def __init__(self, size: int) -> None:
        self._size = size

    def map(self, data: Array) -> Array:
        return data

    def as_indices(self) -> Array:
        return make_array(list(range(self._size)))


class MappedMeshFieldContainer:
    """Wrapper around a mesh field container that transforms the mesh & data"""
    def __init__(self,
                 mesh_fields: MeshFieldContainerInterface,
                 point_map: Optional[MapInterface] = None,
                 cell_maps: Optional[Dict[str, MapInterface]] = None) -> None:
        self._mesh_fields = mesh_fields
        self._point_map = point_map if point_map is not None else _IdentityMap(len(mesh_fields.points))
        self._cell_maps = cell_maps if cell_maps is not None else {
            ct: _IdentityMap(len(mesh_fields.connectivity(ct)))
            for ct in mesh_fields.cell_types
        }
        self._point_index_map_inverse = _make_inverse_index_map(self._point_map.as_indices())

    # Interfaces required to be a "MeshInterface"
    @property
    def cell_types(self) -> Iterable[str]:
        return self._mesh_fields.cell_types

    @property
    def points(self) -> Array:
        return self._transform_point_data(self._mesh_fields.points)

    def connectivity(self, cell_type: str) -> Array:
        return self._transform_cell_data(
            cell_type,
            self._reorder_connectivity(self._mesh_fields.connectivity(cell_type))
        )

    # Interfaces required to be a "MeshFieldContainerInterface"
    def point_data_fields(self) -> Iterable[str]:
        return self._mesh_fields.point_data_fields()

    def cell_data_fields(self, cell_type: str) -> Iterable[str]:
        return self._mesh_fields.cell_data_fields(cell_type)

    def is_point_coordinates_field(self, field_name: str) -> bool:
        return self._mesh_fields.is_point_coordinates_field(field_name)

    def is_cell_corners_field(self, field_name: str, cell_type: str) -> bool:
        return self._mesh_fields.is_cell_corners_field(field_name, cell_type)

    # Interfaces required to be a "FieldContainerInterface"
    @property
    def field_names(self) -> Iterable[str]:
        return self._mesh_fields.field_names

    def get(self, field_name: str) -> Field:
        if self._is_point_data_field(field_name) \
                or self.is_point_coordinates_field(field_name):
            return Field(
                field_name,
                self._transform_point_data(
                    self._mesh_fields.get(field_name).values
                )
            )
        for cell_type in self.cell_types:
            if self._is_cell_data_field(field_name, cell_type):
                return Field(
                    field_name,
                    self._transform_cell_data(
                        cell_type,
                        self._mesh_fields.get(field_name).values
                    )
                )
            if self.is_cell_corners_field(field_name, cell_type):
                return Field(
                    field_name,
                    self.connectivity(cell_type)
                )
        raise ValueError("Could not determine the type of field (coordinates/corners/cell_data/point_data).")

    def __iter__(self) -> Iterator[Field]:
        return iter((self.get(field_name) for field_name in self.field_names))

    # private methods
    def _reorder_connectivity(self, data: Array) -> Array:
        assert len(data.shape) == 2
        result = self._point_index_map_inverse[data]
        return result

    def _transform_point_data(self, data: Array) -> Array:
        return self._point_map.map(data)

    def _transform_cell_data(self, cell_type: str, data: Array) -> Array:
        return self._cell_maps[cell_type].map(data)

    def _is_point_data_field(self, field_name: str) -> bool:
        return any(_fn == field_name for _fn in self.point_data_fields())

    def _is_cell_data_field(self, field_name, cell_type: str) -> bool:
        return any(_fn == field_name for _fn in self.cell_data_fields(cell_type))


def _make_inverse_index_map(forward_map: Array) -> Array:
    max_index = max_element(forward_map)
    inverse = make_uninitialized_array(max_index+1, dtype=int)
    inverse[forward_map] = make_array(list(range(len(forward_map))))
    return inverse
