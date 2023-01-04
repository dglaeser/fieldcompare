"""Reader for extracting fields from csv files"""

import numpy as np

from typing import TextIO, Union

from ..tabular import Table, TabularFields


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
        data = np.genfromtxt(
            input,
            delimiter=self._delimiter,
            names=self._use_names or None,
            skip_header=self._skip_rows,
            dtype=None,
            encoding='UTF-8',
            ndmin=2,
        )

        # make a structured type like for names=True
        if not self._use_names:
            data.dtype = np.dtype([(f"field_{i}", data.dtype) for i in range(data.shape[1])])

        # access arrays by their name
        return TabularFields(
            domain=Table(num_rows=data.shape[0]),
            fields={name: data[name] for name in data.dtype.names},
        )
