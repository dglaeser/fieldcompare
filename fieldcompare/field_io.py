"""Readers of fields from various data formats"""

from array import array
from typing import TextIO, Iterable, Tuple
from os.path import splitext
from json import load
from csv import reader
from numpy import isscalar

from meshio import Mesh
from meshio import read as meshio_read
from meshio import extension_to_filetype as meshio_supported_extensions
from meshio.xdmf import TimeSeriesReader

from fieldcompare import Field, make_array
from fieldcompare.mesh_fields import MeshFields, TimeSeriesMeshFields


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
        idx = self._names.index(name)
        if idx >= len(self._names):
            raise ValueError(f"Could not find the field with name {name}")
        return Field(name, make_array([row[idx] for row in self._data]))

    def field_names(self):
        return self._names

    def _append_data_row(self, row: list) -> None:
        self._data.append([self._convert(v) for v in row])

    def _convert(self, input: str):
        value = _string_to_int(input)
        if value is not None:
            return value
        value = _string_to_float(input)
        if value is not None:
            return value
        return input


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
        for field_name, values in self._fields.items():
            if field_name == name:
                return Field(field_name, values)
        raise ValueError(f"Could not find a field with name {name}")

    def field_names(self):
        return list(self._fields.keys())


def read_fields(filename: str) -> Iterable[Field]:
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
                return _extract_from_meshio_time_series(TimeSeriesReader(filename))
            return _extract_from_meshio_mesh(meshio_read(filename))

    raise NotImplementedError("Unsupported file type")


def _is_supported_field_data_format(field_values: Iterable) -> bool:
    return all(isscalar(value) for value in field_values)


def _string_to_int(input: str):
    try:
        return int(input)
    except ValueError:
        return None


def _string_to_float(input: str):
    try:
        return float(input)
    except ValueError:
        return None


def _convertible_to_float(input: str) -> bool:
    return _string_to_float(input) is not None


def _is_time_series_compatible_format(file_ext: str) -> bool:
    return file_ext in [".xmf", ".xdmf"]


def _extract_from_meshio_mesh(mesh: Mesh) -> MeshFields:
    result = MeshFields(
        mesh.points,
        ((block.type, block.data) for block in mesh.cells)
    )
    for array_name in mesh.point_data:
        result.add_point_data(array_name, mesh.point_data[array_name])
    for array_name in mesh.cell_data:
        result.add_cell_data(
            array_name,
            ((cell_block.type, values) for cell_block, values in zip(mesh.cells, mesh.cell_data[array_name]))
        )
    return result

def _extract_from_meshio_time_series(time_series_reader) -> TimeSeriesMeshFields:
    points, cells = time_series_reader.read_points_cells()
    mesh = Mesh(points, cells)
    time_steps_reader = _MeshioTimeStepReader(mesh, time_series_reader)
    return TimeSeriesMeshFields(
        mesh.points,
        ((block.type, block.data) for block in mesh.cells),
        time_steps_reader
    )

class _MeshioTimeStepReader:
    def __init__(self, mesh: Mesh, reader: TimeSeriesReader) -> None:
        self._mesh = mesh
        self._reader = reader
        self._num_time_steps = reader.num_steps

    @property
    def num_time_steps(self) -> int:
        return self._num_time_steps

    def read_time_step(self, time_step_index: int) -> Tuple:
        _, point_data, cell_data = self._reader.read_data(time_step_index)
        pd = [(name, point_data[name]) for name in point_data]
        cd = [
            (name, [(cell_block.type, values) for cell_block, values in zip(self._mesh.cells, cell_data[name])])
            for name in cell_data
        ]
        return pd, cd
