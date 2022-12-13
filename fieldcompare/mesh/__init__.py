"""Classes and functions related to fields defined on computational meshes"""

from ._mesh import Mesh
from ._permuted_mesh import PermutedMesh
from ._mesh_fields import MeshFields, TransformedMeshFields
from ._io import read, read_sequence, is_mesh_file, is_mesh_sequence
from . import protocols, permutations


def sort(mesh_fields: protocols.MeshFields) -> protocols.MeshFields:
    """Sort the given mesh fields to arrive at a unique representation"""
    return mesh_fields.transformed(
        permutations.remove_unconnected_points
    ).transformed(
        permutations.sort_points
    ).transformed(
        permutations.sort_cells
    )
