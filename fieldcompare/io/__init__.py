"""I/O facilities to read field data from files"""

from os.path import splitext
from typing import Union
from .. import protocols

from . import vtk
from ._csv_reader import CSVFieldReader


def read(filename: str) -> Union[protocols.FieldData, protocols.FieldDataSequence]:
    """Read the field data from the given file"""
    if vtk.is_supported(filename):
        return vtk.read(filename)
    if splitext(filename)[1] == ".csv":
        return CSVFieldReader().read(filename)
    raise IOError(f"Unsupported file '{filename}'")
