"""I/O mechanisms for fields defined on computational meshes"""
from .._field_sequence import FieldDataSequence
from ._vtk import (
    is_supported as is_supported_vtk,
    is_supported_sequence as is_supported_vtk_sequence,
    read as read_vtk,
    read_sequence as read_vtk_sequence
)
from . import meshio_utils
from . import protocols


def is_mesh_file(filename: str) -> bool:
    """Return true if the given file is a (supported) mesh file"""
    if is_supported_vtk(filename):
        return True
    return meshio_utils._is_supported(filename)


def is_mesh_sequence(filename: str) -> bool:
    """Return true if the given file contains a (supported) mesh sequence"""
    return is_supported_vtk_sequence(filename) \
        or meshio_utils._is_supported_sequence(filename)


def read(filename: str) -> protocols.MeshFields:
    """Read the fields from the given mesh file"""
    if is_supported_vtk(filename):
        return read_vtk(filename)
    if meshio_utils._is_supported(filename):
        return meshio_utils._read(filename)
    raise IOError(f"Unsupported mesh file '{filename}'")


def read_sequence(filename: str) -> FieldDataSequence:
    """Read a sequence from the given filename"""
    if is_supported_vtk_sequence(filename):
        return read_vtk_sequence(filename)
    if meshio_utils._is_supported_sequence(filename):
        return meshio_utils._read_sequence(filename)
    raise IOError(f"Unsupported sequence file '{filename}'")
