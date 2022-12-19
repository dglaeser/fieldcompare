"""I/O facilities to read field data from files"""

from os.path import splitext
from typing import Union
from .. import protocols

from . import vtk
from ._csv_reader import CSVFieldReader
from ._mesh_io import (
    _read as _meshio_read,
    _is_supported as _supported_by_meshio,
    _HAVE_MESHIO
)


def read_field_data(filename: str) -> protocols.FieldData:
    """Read the field data from the given file"""
    result = read(filename)
    assert isinstance(result, protocols.FieldData)
    return result


def read(filename: str) -> Union[protocols.FieldData, protocols.FieldDataSequence]:
    """Read the field data or field data sequence from the given file"""
    if vtk.is_supported(filename):
        return vtk.read(filename)
    if splitext(filename)[1] == ".csv":
        return CSVFieldReader().read(filename)
    if _HAVE_MESHIO and _supported_by_meshio(filename):
        try:
            return _meshio_read(filename)
        except IOError as e:
            raise IOError(f"Error reading with meshio: '{e}'")
    raise IOError(
        f"Unsupported file '{filename}'" + (
            "" if _HAVE_MESHIO else " (consider installing 'meshio' to have access to more file formats)"
        )
    )


def is_supported(filename: str) -> bool:
    """Return true if the given file is supported for field-I/O"""
    return vtk.is_supported(filename) \
        or splitext(filename)[1] == ".csv" \
        or _supported_by_meshio(filename)
