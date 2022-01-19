"""Readers of fields from various data formats"""

from typing import TextIO, Iterable, Tuple
from os.path import splitext
from json import load
from csv import reader

from meshio import Mesh
from meshio import read as meshio_read
from meshio import extension_to_filetype as meshio_supported_extensions
from meshio.xdmf import TimeSeriesReader

from ._common import _is_scalar
from .field import Field
from .array import Array, sort_array, sub_array, accumulate
from .array import make_array, make_initialized_array, make_uninitialized_array
from .mesh_fields import MeshFields, TimeSeriesMeshFields


class CSVFieldReader:
    """Read fields from csv files"""

    def __init__(self, file_stream: TextIO):
        self._names: list = []
        self._data: list = []

        csv_reader = reader(file_stream)
        for row_idx, row in enumerate(csv_reader):
            row_values = list(row)
            if row_idx == 0:
                if not any(_convertible_to_float(v) for v in row_values):
                    self._names = row_values
                else:
                    self._names = [f"field_{i}" for i in range(len(row))]
                    self._append_data_row(row_values)
            else:
                self._append_data_row(row_values)

        # ensure there are no duplicate names
        assert len(set(self._names)) == len(self._names)

    def field(self, name: str) -> Field:
        """Return the field with the given name"""
        idx = self._names.index(name)
        if idx >= len(self._names):
            raise ValueError(f"Could not find the field with name {name}")
        return Field(name, make_array([row[idx] for row in self._data]))

    def field_names(self):
        """Return all field names read from the csv file"""
        return self._names

    def _append_data_row(self, row: list) -> None:
        self._data.append([_convert_string(v) for v in row])


class JSONFieldReader:
    """Read fields from json files"""

    def __init__(self, stream: TextIO):
        self._fields: dict = {}
        self._load_fields(load(stream))

    def _load_fields(self, data: dict, key_prefix: str = None) -> None:
        """Read in fields recursively from sub-dictionaries"""
        for key in data:
            field_entry_key = f"{key_prefix}/{key}" if key_prefix is not None else key
            fdata = data[key]
            if isinstance(fdata, dict):
                self._load_fields(fdata, field_entry_key)
            else:
                fdata = [fdata] if not isinstance(fdata, list) else fdata
                if not _is_supported_field_data_format(fdata):
                    raise IOError("Unsupported JSON file layout")
                self._fields[field_entry_key] = fdata

    def field(self, name: str):
        """Return the field with the given name"""
        for field_name, values in self._fields.items():
            if field_name == name:
                return Field(field_name, values)
        raise ValueError(f"Could not find a field with name {name}")

    def field_names(self):
        """Return all fields read from the json file"""
        return list(self._fields.keys())


def read_fields(filename: str, remove_ghost_points: bool = True) -> Iterable[Field]:
    """Read in the fields from the file with the given name"""
    ext = splitext(filename)[1]
    with open(filename, "r") as file_stream:
        if ext == ".json":
            json_reader = JSONFieldReader(file_stream)
            return [json_reader.field(name) for name in json_reader.field_names()]
        if ext == ".csv":
            csv_reader = CSVFieldReader(file_stream)
            return [csv_reader.field(name) for name in csv_reader.field_names()]
        if ext in meshio_supported_extensions:
            if _is_time_series_compatible_format(ext):
                return _extract_from_meshio_time_series(
                        TimeSeriesReader(filename),
                        remove_ghost_points
                    )
            return _extract_from_meshio_mesh(
                    meshio_read(filename),
                    remove_ghost_points
                )
    raise NotImplementedError("Unsupported file type")


def _is_supported_field_data_format(field_values: Iterable) -> bool:
    return all(_is_scalar(value) for value in field_values)


def _convert_string(value_string: str):
    value = _string_to_int(value_string)
    if value is not None:
        return value
    value = _string_to_float(value_string)
    if value is not None:
        return value
    return value_string


def _string_to_int(value_string: str):
    try:
        return int(value_string)
    except ValueError:
        return None


def _string_to_float(value_string: str):
    try:
        return float(value_string)
    except ValueError:
        return None


def _convertible_to_float(value_string: str) -> bool:
    return _string_to_float(value_string) is not None


def _is_time_series_compatible_format(file_ext: str) -> bool:
    return file_ext in [".xmf", ".xdmf"]


def _filter_out_ghost_vertices(mesh: Mesh) -> Tuple[Mesh, Array]:
    is_ghost = make_initialized_array(size=len(mesh.points), dtype=bool, init_value=True)
    for _, corners in _cells(mesh):
        for p_idx in corners.flatten():
            is_ghost[p_idx] = False

    num_ghosts = accumulate(is_ghost)
    first_ghost_index_after_sort = int(len(is_ghost) - num_ghosts)

    ghost_filter_map = sort_array(is_ghost)
    ghost_filter_map = sub_array(ghost_filter_map, 0, first_ghost_index_after_sort)
    ghost_filter_map_inverse = make_uninitialized_array(size=len(mesh.points), dtype=int)
    for new_index, old_index in enumerate(ghost_filter_map):
        ghost_filter_map_inverse[old_index] = new_index

    def _map_corners(corners_array):
        for idx, corners in enumerate(corners_array):
            corners_array[idx] = ghost_filter_map_inverse[corners_array[idx]]
        return corners_array

    return Mesh(
        points=mesh.points[ghost_filter_map],
        cells=[(cell_type, _map_corners(corners)) for cell_type, corners in _cells(mesh)],
        point_data={name: mesh.point_data[name][ghost_filter_map] for name in mesh.point_data},
        cell_data=mesh.cell_data
    ), ghost_filter_map


def _extract_from_meshio_mesh(mesh: Mesh, remove_ghost_points: bool) -> MeshFields:
    if remove_ghost_points:
        mesh, _ = _filter_out_ghost_vertices(mesh)
    result = MeshFields(mesh.points, _cells(mesh))
    for array_name in mesh.point_data:
        result.add_point_data(array_name, mesh.point_data[array_name])
    for array_name in mesh.cell_data:
        result.add_cell_data(
            array_name,
            (
                (cell_type, values)
                for (cell_type, _), values in zip(_cells(mesh), mesh.cell_data[array_name])
            )
        )
    return result


def _extract_from_meshio_time_series(time_series_reader, remove_ghost_points: bool) -> TimeSeriesMeshFields:
    points, cells = time_series_reader.read_points_cells()
    mesh = Mesh(points, cells)
    ghost_point_filter = None
    if remove_ghost_points:
        mesh, ghost_point_filter = _filter_out_ghost_vertices(mesh)
    time_steps_reader = _MeshioTimeStepReader(mesh, time_series_reader, ghost_point_filter)
    return TimeSeriesMeshFields(mesh.points, _cells(mesh), time_steps_reader)


class _MeshioTimeStepReader:
    def __init__(self,
                 mesh: Mesh,
                 meshio_reader: TimeSeriesReader,
                 ghost_point_filter: Array = None) -> None:
        self._mesh = mesh
        self._reader = meshio_reader
        self._num_time_steps = meshio_reader.num_steps
        self._ghost_point_filter = ghost_point_filter

    @property
    def num_time_steps(self) -> int:
        """Return the number of time steps that can be read"""
        return self._num_time_steps

    def read_time_step(self, time_step_index: int) -> Tuple:
        """Read the time step with the given index"""
        _, point_data, cell_data = self._reader.read_data(time_step_index)
        point_data = [
            (name, self._transform_point_data(point_data[name]))
            for name in point_data
        ]
        cell_data = [
            (
                name,
                [
                    (cell_type, values)
                    for (cell_type, _), values in zip(_cells(self._mesh), cell_data[name])
                ]
            )
            for name in cell_data
        ]
        return point_data, cell_data

    def _transform_point_data(self, point_data: Array) -> Array:
        if self._ghost_point_filter is not None:
            return point_data[self._ghost_point_filter]
        return point_data


def _cells(mesh: Mesh) -> Iterable[Tuple[str, Array]]:
    return ((cell_block.type, cell_block.data) for cell_block in mesh.cells)
