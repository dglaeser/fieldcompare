"""Utility functions for interoperability with meshio"""

from typing import Dict, List
from meshio import Mesh as MeshIOMesh
from numpy.typing import ArrayLike

from ._mesh_fields import MeshFields, remove_cell_type_suffix
from ._mesh import Mesh
from .protocols import MeshFields as MeshFieldsInterface


def from_meshio(mesh: MeshIOMesh) -> MeshFields:
    """Convert a mesh data structure of the meshio library into MeshFields"""
    return MeshFields(
        mesh=Mesh(
            mesh.points,
            (
                (block.type, block.data)
                for block in mesh.cells
            )
        ),
        point_data=mesh.point_data,
        cell_data=mesh.cell_data
    )


def to_meshio(mesh_fields: MeshFieldsInterface) -> MeshIOMesh:
    """Convert MeshFields into a mesh of the meshio library"""
    types = [ct for ct in mesh_fields.domain.cell_types]
    cell_data: Dict[str, List[ArrayLike]] = {}
    for field, cell_type in mesh_fields.cell_fields_types:
        name = remove_cell_type_suffix(cell_type, field.name)
        if name not in cell_data:
            cell_data[name] = [[] for _ in range(len(types))]
        cell_data[name][types.index(cell_type)] = [v for v in field.values]

    return MeshIOMesh(
        points=mesh_fields.domain.points,
        cells={ct: mesh_fields.domain.connectivity(ct) for ct in types},
        point_data={field.name: field.values for field in mesh_fields.point_fields},
        cell_data={name: data for name, data in cell_data.items()}
    )
