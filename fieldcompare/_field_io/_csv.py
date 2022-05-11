"""Reader for extracting fields from csv files"""

from csv import reader

from ..field import Field, DefaultFieldContainer
from ..array import make_array
from ..logging import LoggableBase
from ._common import _convert_string, _convertible_to_float
from ._reader_map import _register_reader_for_extension


class CSVFieldReader(LoggableBase):
    """Read fields from csv files"""

    def read(self, filename: str) -> DefaultFieldContainer:
        names = []
        rows = []

        with open(filename) as file_stream:
            csv_reader = reader(file_stream)
            for row_idx, row in enumerate(csv_reader):
                row_values = list(row)
                if row_idx == 0:
                    if not any(_convertible_to_float(v) for v in row_values):
                        self._log(
                            "Using first row as field names\n",
                            verbosity_level=2
                        )
                        names = row_values
                    else:
                        self._log(
                            "Could not use first row as field names, using 'field_i'\n",
                            verbosity_level=2
                        )
                        names = [f"field_{i}" for i in range(len(row))]
                        rows.append([_convert_string(v) for v in row_values])
                else:
                    rows.append([_convert_string(v) for v in row_values])

        return DefaultFieldContainer([
            Field(
                names[col_idx],
                make_array([rows[i][col_idx] for i in range(len(rows))])
            )
            for col_idx in range(len(names))
        ])


_register_reader_for_extension(".csv", CSVFieldReader())
