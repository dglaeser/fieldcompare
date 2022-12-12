from os.path import splitext

from ._tabular_fields import Table, TabularFields
from ._csv_field_reader import CSVFieldReader


def is_tabular_data_file(filename: str) -> bool:
    """Return true if the given file contains (supported) tabular data"""
    return splitext(filename)[1] == ".csv"


def is_tabular_data_sequence(filename: str) -> bool:
    """Return true if the tabular data file contains a sequence of field data"""
    return False


def read(filename: str, delimiter: str = ",", use_names: bool = True) -> TabularFields:
    """Read the tabular data from the given file"""
    ext = splitext(filename)[1]
    if ext == ".csv":
        return CSVFieldReader(delimiter=delimiter, use_names=use_names).read(filename)
    raise NotImplementedError(f"No support for tabular data I/O for files with extension '{ext}'")
