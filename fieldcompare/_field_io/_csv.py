"""Reader for extracting fields from csv files"""

from typing import TextIO, Iterable
from csv import reader

from ..field import Field
from ..array import make_array
from ._common import _convert_string, _convertible_to_float
from ._reader_map import _register_reader_for_extension


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


def _read_fields_from_csv_file(filename: str, remove_ghost_points: bool) -> Iterable[Field]:
    with open(filename) as file_stream:
        csv_reader = CSVFieldReader(file_stream)
        return [csv_reader.field(name) for name in csv_reader.field_names()]

_register_reader_for_extension(".csv", _read_fields_from_csv_file)
