"""I/O facilities to read field data from files"""

from os.path import splitext
from typing import Union
from .. import protocols

from . import vtk
from ._csv_reader import CSVFieldReader
from ._mesh_io import _read as _meshio_read, _HAVE_MESHIO


def read(filename: str) -> Union[protocols.FieldData, protocols.FieldDataSequence]:
    """Read the field data from the given file"""
    if vtk.is_supported(filename):
        return vtk.read(filename)
    if splitext(filename)[1] == ".csv":
        return CSVFieldReader().read(filename)
    if _HAVE_MESHIO:
        try:
            return _meshio_read(filename)
        except IOError as e:
            raise IOError(f"Error reading with meshio: '{e}'")
    raise IOError(
        f"Unsupported file '{filename}'" + (
        "" if _HAVE_MESHIO else " (consider installing 'meshio' to have access to more file formats)"
        )
    )
