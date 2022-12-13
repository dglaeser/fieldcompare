"""Classes and functions related to fields defined on computational meshes"""

from ._mesh import Mesh
from ._permuted_mesh import PermutedMesh
from ._mesh_fields import MeshFields, PermutedMeshFields
from ._io import read, read_sequence, is_mesh_file, is_mesh_sequence
from . import protocols, permutations


def sort(mesh_fields: protocols.MeshFields) -> protocols.MeshFields:
    """Sort the given mesh fields to arrive at a unique representation"""
    return mesh_fields.permuted(
        permutations.remove_unconnected_points
    ).permuted(
        permutations.sort_points
    ).permuted(
        permutations.sort_cells
    )
