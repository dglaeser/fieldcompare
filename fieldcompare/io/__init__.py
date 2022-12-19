"""I/O facilities to read field data from files"""

from typing import Union
from .. import protocols

from . import vtk


def read(filename: str) -> Union[protocols.FieldData, protocols.FieldDataSequence]:
    """Read the field data from the given file"""
    if vtk.is_supported(filename):
        return vtk.read(filename)
    raise IOError(f"Unsupported file '{filename}'")
