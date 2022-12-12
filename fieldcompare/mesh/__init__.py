"""Classes and functions related to fields defined on computational meshes"""

from ._mesh import Mesh
from ._permuted_mesh import PermutedMesh
from ._mesh_fields import MeshFields, PermutedMeshFields
from ._io import read, read_sequence, is_mesh_file, is_mesh_sequence
from . import protocols, permutations


def sort(mesh_fields: protocols.MeshFields) -> PermutedMeshFields:
    """Sort the given mesh fields to arrive at a unique representation"""
    return mesh_fields.permuted(
        permutations.remove_unconnected_points
    ).permuted(
        permutations.sort_points
    ).permuted(
        permutations.sort_cells
    )


def sort_mesh(mesh: protocols.Mesh) -> PermutedMesh:
    """Sort the given mesh to arrive at a unique representation"""
    return permutations.sort_cells(
        permutations.sort_points(
            permutations.remove_unconnected_points(mesh)
        )
    )
