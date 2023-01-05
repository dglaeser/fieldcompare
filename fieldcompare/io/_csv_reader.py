"""Reader for extracting fields from csv files"""

import csv
import numpy as np

from typing import TextIO, Union, Optional, Callable, TypeVar

from ..tabular import Table, TabularFields


class CSVFieldReader:
    """Read fields from csv files"""

    def __init__(self, delimiter: Optional[str] = None, use_names: Optional[bool] = None, skip_rows: int = 0) -> None:
        self._delimiter = delimiter
        self._use_names = use_names
        self._skip_rows = skip_rows

    def read(self, input: Union[str, TextIO]) -> TabularFields:
        delimiter = self._delimiter if self._delimiter is not None else self._sniff_delimiter(input)
        use_names = self._use_names if self._use_names is not None else self._sniff_header(input)
        data = np.genfromtxt(
            input,
            delimiter=delimiter,
            names=use_names or None,
            skip_header=self._skip_rows,
            dtype=None,
            encoding="UTF-8",
            ndmin=2,
        )

        if not use_names:
            # overwrite with our default field names
            # create a structured type if it isn't one yet
            if data.dtype.names is None:
                num_fields = 0 if len(data) == 0 else len(data[0])
                data = data.astype(np.dtype([(f"field_{i}", data.dtype) for i in range(num_fields)]))
            else:
                data.dtype.names = tuple(f"field_{i}" for i in range(len(data.dtype.names)))

        # access arrays by their name
        return TabularFields(
            domain=Table(num_rows=data.shape[0]),
            fields={name: data[name] for name in data.dtype.names},  # type: ignore
        )

    def _sniff_delimiter(self, input: Union[str, TextIO]) -> str:
        return self._sniff(input, action=lambda f: csv.Sniffer().sniff(f.read(1024)).delimiter)

    def _sniff_header(self, input: Union[str, TextIO]) -> bool:
        return self._sniff(input, action=lambda f: csv.Sniffer().has_header(f.read(1024)))

    T = TypeVar("T")

    def _sniff(self, input: Union[str, TextIO], action: Callable[[TextIO], T]) -> T:
        def _call_action(file: TextIO):
            current_pos = file.tell()
            result = action(file)
            file.seek(current_pos)
            return result

        if isinstance(input, str):
            with open(input) as csv_file:
                return _call_action(csv_file)
        return _call_action(input)
