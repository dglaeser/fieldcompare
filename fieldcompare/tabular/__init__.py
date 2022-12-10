from os.path import splitext

from ._tabular_fields import Table, TabularFields
from ._csv_field_reader import CSVFieldReader


def read(filename: str, delimiter: str = ",", use_names: bool = True) -> TabularFields:
    """Read the tabular data from the given file"""
    ext = splitext(filename)
    if ext == ".csv":
        return CSVFieldReader(delimiter=delimiter, use_names=use_names).read(filename)
    raise NotImplementedError(f"Tabular data reading for files with extension {ext}")
