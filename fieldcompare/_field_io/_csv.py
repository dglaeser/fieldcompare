"""Reader for extracting fields from csv files"""

from typing import List
from csv import reader

from ..field import Field
from ..array import make_array
from ..logging import Logger, NullDeviceLogger
from ._common import _convert_string, _convertible_to_float
from ._reader_map import _register_reader_for_extension


class CSVFieldReader:
    """Read fields from csv files"""

    def __init__(self, logger: Logger = NullDeviceLogger()) -> None:
        self._logger = logger

    def attach_logger(self, logger: Logger) -> None:
        self._logger = logger

    def read(self, filename: str) -> List[Field]:
        names = []
        rows = []

        with open(filename) as file_stream:
            csv_reader = reader(file_stream)
            for row_idx, row in enumerate(csv_reader):
                row_values = list(row)
                if row_idx == 0:
                    if not any(_convertible_to_float(v) for v in row_values):
                        self._logger.log(
                            "Using first row as field names\n",
                            verbosity_level=2
                        )
                        names = row_values
                    else:
                        self._logger.log(
                            "Could not use first row as field names, using 'field_i'\n",
                            verbosity_level=2
                        )
                        names = [f"field_{i}" for i in range(len(row))]
                        rows.append([_convert_string(v) for v in row_values])
                else:
                    rows.append([_convert_string(v) for v in row_values])

        return [
            Field(
                names[col_idx],
                make_array([rows[i][col_idx] for i in range(len(rows))])
            )
            for col_idx in range(len(names))
        ]


_register_reader_for_extension(".csv", CSVFieldReader())
