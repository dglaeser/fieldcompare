"""I/O mechanisms for fields defined on computational meshes"""
from meshio import read as _meshio_read

from ._mesh_fields import MeshFields
from .meshio_utils import from_meshio


def read(filename: str) -> MeshFields:
    """Read the fields from the given mesh file"""
    return from_meshio(_meshio_read(filename))
