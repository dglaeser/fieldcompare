"""Reader for extracting fields from csv files"""

import csv
import numpy as np

from typing import TextIO, Union, Optional

from ..tabular import Table, TabularFields


class CSVFieldReader:
    """Read fields from csv files"""

    def __init__(self, delimiter: Optional[str] = None, use_names: bool = True, skip_rows: int = 0) -> None:
        self._delimiter = delimiter
        self._use_names = use_names
        self._skip_rows = skip_rows

    def read(self, input: Union[str, TextIO]) -> TabularFields:
        delimiter = self._delimiter if self._delimiter is not None else self._sniff_delimiter(input)
        data = np.genfromtxt(
            input,
            delimiter=delimiter,
            names=self._use_names or None,
            skip_header=self._skip_rows,
            dtype=None,
            encoding="UTF-8",
            ndmin=2,
        )

        # (maybe) overwrite with our default field names
        if not self._use_names:
            num_fields = (
                len(data.dtype.names) if data.dtype.names is not None else (len(data[0]) if len(data) > 0 else 0)
            )
            data.dtype.names = tuple(f"field_{i}" for i in range(num_fields))

        # access arrays by their name
        return TabularFields(
            domain=Table(num_rows=data.shape[0]),
            fields={name: data[name] for name in data.dtype.names},  # type: ignore
        )

    def _sniff_delimiter(self, input: Union[str, TextIO]) -> str:
        def _delimiter(file: TextIO) -> str:
            current_pos = file.tell()
            delimiter = csv.Sniffer().sniff(file.read(1024)).delimiter
            file.seek(current_pos)
            return delimiter

        if isinstance(input, str):
            with open(input) as file:
                return _delimiter(file=file)

        return _delimiter(file=input)
