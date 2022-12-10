"""Reader for extracting fields from csv files"""

from csv import reader
from typing import TextIO, List, Union

from .._array import make_array
from ._common import _convert_string

from ._table import Table
from ._tabular_fields import TabularFields


class CSVFieldReader:
    """Read fields from csv files"""
    def __init__(self,
                 delimiter=",",
                 use_names: bool = True,
                 skip_rows: int = 0) -> None:
        self._delimiter = delimiter
        self._use_names = use_names
        self._skip_rows = skip_rows

    def read(self, input: Union[str, TextIO]) -> TabularFields:
        if isinstance(input, str):
            return self._read_from_stream(open(input))
        return self._read_from_stream(input)

    def _read_from_stream(self, stream: TextIO) -> TabularFields:
        for _ in range(self._skip_rows):
            stream.readline()

        rows = []
        names = None

        def _append_row(row_string_values: List[str]):
            rows.append([_convert_string(v) for v in row_string_values])

        if self._use_names:
            names = self._read_names(stream)
        else:
            _append_row(stream.readline().strip("\n").split(self._delimiter))
            names = [f"field_{i}" for i in range(len(rows[0]))]

        for row in reader(stream, delimiter=self._delimiter):
            _append_row(list(row))

        return TabularFields(
            domain=Table(num_rows=len(rows)),
            fields={
                names[col_idx]: make_array([rows[i][col_idx] for i in range(len(rows))])
                for col_idx in range(len(names))
            }
        )

    def _read_names(self, stream: TextIO) -> List[str]:
        line = stream.readline()
        return line.strip("\n").split(self._delimiter)
