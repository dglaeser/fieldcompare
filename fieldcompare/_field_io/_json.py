"""Reader for extracting fields from json files"""

from typing import TextIO, Iterable
from json import load

from ..field import Field
from ._common import _is_supported_field_data_format
from ._reader_map import _register_reader_for_extension


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


def _read_fields_from_json_file(filename: str, remove_ghost_points: bool) -> Iterable[Field]:
    with open(filename) as file_stream:
        json_reader = JSONFieldReader(file_stream)
        return [json_reader.field(name) for name in json_reader.field_names()]

_register_reader_for_extension(".json", _read_fields_from_json_file)
