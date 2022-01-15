"""Readers of fields from various data formats"""

from multiprocessing.sharedctypes import Value
from typing import TextIO, Iterable, List
from os.path import splitext
from json import load
from csv import reader
from numpy import isscalar

from meshio import Mesh
from meshio import read as meshio_read
from meshio import extension_to_filetype as meshio_supported_extensions

from fieldcompare import Field, make_array
from fieldcompare.mesh_fields import MeshFields


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


def read_fields(filename: str) -> List[Field]:
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
                raise NotImplementedError("Time series")
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
    return MeshFields(
        mesh.points,
        ((block.type, block.data) for block in mesh.cells)
    )
