from os.path import splitext

from .._mesh_fields import MeshFields
from ._vtu_reader import VTUReader


def read(filename: str) -> MeshFields:
    ext = splitext(filename)[1]
    if ext == ".vtu":
        return VTUReader(filename).read()
    raise NotImplementedError(f"Unsupported VTK file extension '{ext}'")
