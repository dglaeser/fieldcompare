from os.path import splitext

from ..._field_sequence import FieldDataSequence
from .._mesh_fields import MeshFields
from ._vtu_reader import VTUReader


_VTK_MESH_EXTENSIONS_TO_READER = {
    ".vtu": VTUReader
}


def read(filename: str) -> MeshFields:
    """Read mesh fields from the given VTK file"""
    ext = splitext(filename)[1]
    if ext not in _VTK_MESH_EXTENSIONS_TO_READER:
        raise IOError(f"Unsupported VTK file extension '{ext}'")
    return _VTK_MESH_EXTENSIONS_TO_READER[ext](filename).read()


def read_sequence(filename: str) -> FieldDataSequence:
    """Read a sequence from a VTK file"""
    raise IOError(f"Unsupported VTK sequence file '{filename}'")


def is_supported(filename: str) -> bool:
    """Return true if the given VTK file is supported"""
    return splitext(filename)[1] in _VTK_MESH_EXTENSIONS_TO_READER


def is_supported_sequence(filename: str) -> bool:
    """Return true if the given VTK sequence file is supported"""
    return False
