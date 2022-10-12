"""Containers for fields defined on meshes"""

from typing import Iterable, List, Dict, Protocol, Iterator, Tuple, Callable, Optional
from functools import partial

from .._field import Field, FieldContainerInterface
from .._array import Array


Points = Array
PointData = Dict[str, Array]
CellData = Dict[str, Dict[str, Array]]


class MeshInterface(Protocol):
    """Interface for meshes"""
    @property
    def points(self) -> Points:
        """Return the points of this mesh"""
        ...

    @property
    def cell_types(self) -> Iterable[str]:
        """Return the cell types present in this mesh"""
        ...

    def connectivity(self, cell_type: str) -> Array:
        """Return the corner indices array for the cells of the given type"""
        ...


class MeshFieldContainerInterface(
        FieldContainerInterface,
        MeshInterface,
        Protocol):
    """Interface for field containers on meshes"""

    def point_data_fields(self) -> Iterable[str]:
        """Return the names of the fields that live on points"""
        ...

    def cell_data_fields(self, cell_type: str) -> Iterable[str]:
        """Return the names of the fields that live on cells of the given type"""
        ...

    def is_point_coordinates_field(self, field_name: str) -> bool:
        """Return true if the given field represents the point coordinates of the mesh"""
        ...

    def is_cell_corners_field(self, field_name: str, cell_type: str) -> bool:
        """Return true if the given field represents the corners of the cells of given type"""
        ...


class MeshFieldContainer:
    def __init__(self,
                 mesh: MeshInterface,
                 point_data: PointData,
                 cell_data: CellData) -> None:
        self._mesh = mesh
        self._point_data = point_data
        self._cell_data = cell_data

        self._field_values: Dict[str, Array] = {}
        self._point_data_fields: List[str] = []
        self._cell_data_fields: dict = {cell_type: [] for cell_type in mesh.cell_types}
        self._register_field_values()

    # Interfaces required to be a "MeshInterface"
    @property
    def points(self) -> Array:
        return self._mesh.points

    @property
    def cell_types(self) -> Iterable[str]:
        return self._mesh.cell_types

    def connectivity(self, cell_type: str) -> Array:
        return self._mesh.connectivity(cell_type)

    # Interfaces required to be a "MeshFieldContainerInterface"
    def point_data_fields(self) -> Iterable[str]:
        return self._point_data_fields

    def cell_data_fields(self, cell_type: str) -> Iterable[str]:
        return self._cell_data_fields[cell_type]

    def is_point_coordinates_field(self, field_name: str) -> bool:
        return field_name == _point_coordinates_field_name()

    def is_cell_corners_field(self, field_name: str, cell_type: str) -> bool:
        return cell_type in self.cell_types and _is_cell_corners_field_name(field_name, cell_type)

    # Interfaces required to be a "FieldContainerInterface"
    @property
    def field_names(self) -> Iterable[str]:
        return self._field_values.keys()

    def get(self, field_name: str) -> Field:
        return Field(field_name, self._field_values[field_name])

    def __iter__(self) -> Iterator[Field]:
        return iter((self.get(field_name) for field_name in self.field_names))

    # private methods
    def _register_field_values(self) -> None:
        self._register_point_coordinate_field()
        self._register_cell_corner_fields()
        self._register_point_data_fields()
        self._register_cell_data_fields()

    def _register_point_coordinate_field(self) -> None:
        name = _point_coordinates_field_name()
        self._field_values[name] = self._mesh.points

    def _register_cell_corner_fields(self) -> None:
        for cell_type in self._mesh.cell_types:
            name = _make_cell_corners_field_name(cell_type)
            self._field_values[name] = self._mesh.connectivity(cell_type)

    def _register_point_data_fields(self) -> None:
        for name in self._point_data:
            self._field_values[name] = self._point_data[name]
            self._point_data_fields.append(name)

    def _register_cell_data_fields(self) -> None:
        for name in self._cell_data:
            for cell_type in self._cell_data[name]:
                field_name = _make_cell_type_field_name(name, cell_type)
                self._field_values[field_name] = self._cell_data[name][cell_type]
                self._cell_data_fields[cell_type].append(field_name)


class TimeSeriesReaderInterface(Protocol):
    @property
    def num_time_steps(self) -> int:
        """Return the total number of timesteps"""
        ...

    def point_data_names_of_time_step(self, time_step_index: int) -> Iterable[str]:
        """Return the names of the point data fields of the given time step"""
        ...

    def cell_data_names_of_time_step(self, time_step_index: int) -> Iterable[str]:
        """Return the names of the cell data fields of the given time step"""
        ...

    def read_time_step(self, time_step_index: int) -> Tuple[PointData, CellData]:
        """Return the point and cell data of the given time step"""
        ...


_FieldValuesAccessor = Callable[[], Array]
class TimeSeriesMeshFieldContainer:
    """
        A field container that contains the fields of multiple time steps on a mesh.
        To save memory, it never stores more than the fields of one time step.
        If the fields of the next time step are requested, they are read in lazily.
    """
    _time_step_field_name_suffix = "_timestep_"

    def __init__(self,
                 mesh: MeshInterface,
                 time_series_reader: TimeSeriesReaderInterface) -> None:
        self._mesh = mesh
        self._time_series_reader = time_series_reader

        self._time_step_idx = -1
        self._point_data: Optional[PointData] = None
        self._cell_data: Optional[CellData] = None

        self._field_value_accessors: Dict[str, _FieldValuesAccessor] = {}
        self._point_data_fields: List[str] = []
        self._cell_data_fields: dict = {cell_type: [] for cell_type in mesh.cell_types}
        self._register_field_accessors()

    # Interfaces required to be a "MeshInterface"
    @property
    def points(self) -> Array:
        return self._mesh.points

    @property
    def cell_types(self) -> Iterable[str]:
        return self._mesh.cell_types

    def connectivity(self, cell_type: str) -> Array:
        return self._mesh.connectivity(cell_type)

    # Interfaces required to be a "MeshFieldContainerInterface"
    def point_data_fields(self) -> Iterable[str]:
        return self._point_data_fields

    def cell_data_fields(self, cell_type: str) -> Iterable[str]:
        return self._cell_data_fields[cell_type]

    def is_point_coordinates_field(self, field_name: str) -> bool:
        return field_name == _point_coordinates_field_name()

    def is_cell_corners_field(self, field_name: str, cell_type: str) -> bool:
        return _is_cell_corners_field_name(field_name, cell_type)

    # Interfaces required to be a "FieldContainerInterface"
    @property
    def field_names(self) -> Iterable[str]:
        return self._field_value_accessors.keys()

    def get(self, field_name: str) -> Field:
        if field_name == _point_coordinates_field_name() \
                or self._is_cell_corners_field_name(field_name):
            return Field(field_name, self._field_value_accessors[field_name]())

        step_idx = _deduce_time_step_from_field_name(field_name)
        self._prepare_data_for_time_step(step_idx)
        return Field(field_name, self._field_value_accessors[field_name]())

    def __iter__(self) -> Iterator[Field]:
        return iter((self.get(field_name) for field_name in self.field_names))

    # private methods
    def _register_field_accessors(self) -> None:
        self._register_point_coordinates_accessor()
        self._register_cell_corners_accessors()
        for step_idx in range(self._time_series_reader.num_time_steps):
            self._register_point_data_field_accessors(step_idx)
            self._register_cell_data_field_accessors(step_idx)

    def _register_point_coordinates_accessor(self) -> None:
        self._field_value_accessors[_point_coordinates_field_name()] = lambda: self._mesh.points

    def _register_cell_corners_accessors(self) -> None:
        for cell_type in self._mesh.cell_types:
            name = _make_cell_corners_field_name(cell_type)
            self._field_value_accessors[name] = lambda: self._mesh.connectivity(cell_type)

    def _register_point_data_field_accessors(self, step_idx: int) -> None:
        for name in self._time_series_reader.point_data_names_of_time_step(step_idx):
            name_with_suffix = _make_step_field_name(step_idx, name)
            self._field_value_accessors[name_with_suffix] = partial(
                self._get_point_data, name=name, step_idx=step_idx
            )
            self._point_data_fields.append(name_with_suffix)

    def _register_cell_data_field_accessors(self, step_idx: int) -> None:
        for name in self._time_series_reader.cell_data_names_of_time_step(step_idx):
            for cell_type in self._mesh.cell_types:
                name_with_suffixes = _make_cell_type_field_name(name, cell_type)
                name_with_suffixes = _make_step_field_name(step_idx, name_with_suffixes)
                self._field_value_accessors[name_with_suffixes] = partial(
                    self._get_cell_data, name=name, cell_type=cell_type, step_idx=step_idx
                )
                self._cell_data_fields[cell_type].append(name_with_suffixes)

    def _get_point_data(self, name: str, step_idx: int) -> Array:
        self._prepare_data_for_time_step(step_idx)
        assert self._point_data is not None
        return self._point_data[name]

    def _get_cell_data(self, name: str, cell_type: str, step_idx: int) -> Array:
        self._prepare_data_for_time_step(step_idx)
        assert self._cell_data is not None
        return self._cell_data[name][cell_type]

    def _prepare_data_for_time_step(self, step_idx: int) -> None:
        if step_idx != self._time_step_idx:
            self._point_data, self._cell_data = self._time_series_reader.read_time_step(step_idx)

    def _is_cell_corners_field_name(self, field_name: str) -> bool:
        return any(
            _is_cell_corners_field_name(field_name, cell_type)
            for cell_type in self.cell_types
        )


def _make_step_field_name(step_idx: int, name: str) -> str:
    return f"{name}_timestep_{step_idx}"


def _deduce_time_step_from_field_name(name: str) -> int:
    return int(name.rsplit("_timestep_")[1])


def _point_coordinates_field_name() -> str:
    return "point_coordinates"


def _add_cell_type_suffix(field_name: str, cell_type: str) -> str:
    return f"{field_name}_{cell_type}"


def _make_cell_type_field_name(field_name: str, cell_type: str) -> str:
    return _add_cell_type_suffix(field_name, cell_type)


def _make_cell_corners_field_name(cell_type: str) -> str:
    return f"{cell_type}_corners"

def _is_cell_corners_field_name(field_name: str, cell_type: str) -> bool:
    count = field_name.count(f"{cell_type}_corners")
    if count > 1:
        raise ValueError("Cannot deduce if the given field represents cell corners")
    return count > 0
