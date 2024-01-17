# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Utility functions for interoperability with meshio"""

from __future__ import annotations
from numpy import ndarray
from numpy.typing import ArrayLike

from meshio import Mesh as MeshIOMesh
from meshio._vtk_common import vtk_to_meshio_type, meshio_to_vtk_type  # type: ignore[import]

# meshio uses the same cell-type indexing as VTK,
# so we transform names/indices for compatibility
from ..io.vtk._helpers import vtk_cell_type_index_to_cell_type, cell_type_to_vtk_cell_type_index

from ._mesh import Mesh
from ._cell_type import CellType, CellTypes, _reorder_hex_voxel, _reorder_quad_pixel
from ._mesh_fields import MeshFields, remove_cell_type_suffix
from . import protocols


def from_meshio(mesh: MeshIOMesh) -> MeshFields:
    """Convert a mesh data structure of the meshio library into MeshFields"""
    return MeshFields(
        mesh=Mesh(mesh.points, ((_from_meshio_cell_type(block.type), block.data) for block in mesh.cells)),
        point_data=mesh.point_data,
        cell_data=mesh.cell_data,
    )


def to_meshio(mesh_fields: protocols.MeshFields) -> MeshIOMesh:
    """Convert MeshFields into a mesh of the meshio library"""
    types = [ct for ct in mesh_fields.domain.cell_types]
    cell_data: dict[str, list[ArrayLike]] = {}
    for field, cell_type in mesh_fields.cell_fields_types:
        name = remove_cell_type_suffix(cell_type, field.name)
        if name not in cell_data:
            cell_data[name] = [[] for _ in range(len(types))]
        cell_data[name][types.index(cell_type)] = [v for v in field.values]

    cells: dict[str, ndarray] = {}
    for cell_type in types:
        meshio_ct, meshio_connectivity = _to_meshio_cell_type_and_ordering(
            cell_type, mesh_fields.domain.connectivity(cell_type)
        )
        cells[meshio_ct] = meshio_connectivity

    return MeshIOMesh(
        points=mesh_fields.domain.points,
        cells=cells,
        point_data={field.name: field.values for field in mesh_fields.point_fields},
        cell_data={name: data for name, data in cell_data.items()},
    )


def _from_meshio_cell_type(cell_type: str) -> CellType:
    return vtk_cell_type_index_to_cell_type(meshio_to_vtk_type[cell_type])


def _to_meshio_cell_type_and_ordering(cell_type: CellType, connectivity: ndarray) -> tuple[str, ndarray]:
    reordered = connectivity
    if cell_type.name in meshio_to_vtk_type:
        return str(cell_type), reordered

    # meshio does not support pixels/voxels -> use quads/hexes
    if cell_type == CellTypes.pixel:
        cell_type = CellTypes.quad
        for i in range(len(connectivity)):
            reordered[i] = _reorder_quad_pixel(connectivity[i])
    if cell_type == CellTypes.voxel:
        cell_type = CellTypes.hexahedron
        for i in range(len(connectivity)):
            reordered[i] = _reorder_hex_voxel(connectivity[i])

    return vtk_to_meshio_type[cell_type_to_vtk_cell_type_index(cell_type)], reordered
