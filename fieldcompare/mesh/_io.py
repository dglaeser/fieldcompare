"""I/O mechanisms for fields defined on computational meshes"""
from .._field_sequence import FieldDataSequence
from ._mesh_fields import MeshFields
from ._vtk import is_supported as is_supported_vtk, read as read_vtk
from . import meshio_utils


def is_mesh_file(filename: str) -> bool:
    """Return true if the given file is a (supported) mesh file"""
    if is_supported_vtk(filename):
        return True
    return meshio_utils._is_supported(filename)


def is_mesh_sequence(filename: str) -> bool:
    """Return true if the given file contains a (supported) mesh sequence"""
    return meshio_utils._is_supported_sequence(filename)


def read(filename: str) -> MeshFields:
    """Read the fields from the given mesh file"""
    if is_supported_vtk(filename):
        return read_vtk(filename)
    if meshio_utils._is_supported(filename):
        return meshio_utils._read(filename)
    raise IOError(f"Unsupported mesh file '{filename}'")


def read_sequence(filename: str) -> FieldDataSequence:
    """Read a sequence from the given filename"""
    if meshio_utils._is_supported_sequence(filename):
        return meshio_utils._read_sequence(filename)
    raise IOError(f"Unsupported sequence file '{filename}'")
