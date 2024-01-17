# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Class to represent the type of a mesh cell"""

from __future__ import annotations
from typing import List

from .._numpy_utils import Array, make_array
from ._cell_type_maps import _CELL_TYPE_INDEX_TO_STR, _CELL_TYPE_STR_TO_INDEX


class CellType:
    """
    Represents the type of a mesh cell.

    Args:
        id: The cell type id (we reuse the ids of VTK, see https://vtk.org/doc/nightly/html/vtkCellType_8h_source.html).
    """

    def __init__(self, id: int) -> None:
        if id not in _CELL_TYPE_INDEX_TO_STR:
            raise ValueError(f"Unknown cell type with id '{id}'")
        self._id = id

    @property
    def id(self) -> int:
        """Return the type id of this cell type."""
        return self._id

    @property
    def name(self) -> str:
        """Return the name of this cell type."""
        return _CELL_TYPE_INDEX_TO_STR[self._id]

    def is_compatible_with(self, other: CellType) -> bool:
        """Return true if the given cell type may be compatible with this one"""
        if self._id == other._id:
            return True
        return other.id in _COMPATIBLES.get(self._id, [])

    def __repr__(self) -> str:
        return f"CellType('{self.name}')"

    def __hash__(self) -> int:
        return hash(self._id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CellType):
            return NotImplemented
        return self._id == other._id

    @staticmethod
    def from_name(name: str) -> CellType:
        """
        Return the cell type with the given name.

        Args:
            name: The cell type name.
        """
        try:
            return CellType(_CELL_TYPE_STR_TO_INDEX[name])
        except KeyError:
            raise ValueError(f"Unknown cell type with name '{name}'") from None


class CellTypes:
    """Predefined cell type instances for the most commonly used ones"""

    vertex = CellType.from_name("VERTEX")
    line = CellType.from_name("LINE")
    triangle = CellType.from_name("TRIANGLE")
    polygon = CellType.from_name("POLYGON")
    pixel = CellType.from_name("PIXEL")
    quad = CellType.from_name("QUAD")
    tetra = CellType.from_name("TETRA")
    voxel = CellType.from_name("VOXEL")
    hexahedron = CellType.from_name("HEXAHEDRON")
    pyramid = CellType.from_name("PYRAMID")


def _reorder_quad_pixel(connectivity: Array) -> Array:
    idx_map = make_array([0, 1, 3, 2])
    return connectivity[idx_map]


def _reorder_hex_voxel(connectivity: Array) -> Array:
    idx_map = make_array([0, 1, 3, 2, 4, 5, 7, 6])
    return connectivity[idx_map]


_COMPATIBLES: dict[int, List[int]] = {}


def _insert_compatibles(ct1: CellType, ct2: CellType) -> None:
    for id1, id2 in [(ct1.id, ct2.id), (ct2.id, ct1.id)]:
        if id1 not in _COMPATIBLES:
            _COMPATIBLES[id1] = []
        if id2 not in _COMPATIBLES[id1]:
            _COMPATIBLES[id1].append(id2)


_insert_compatibles(CellTypes.quad, CellTypes.pixel)
_insert_compatibles(CellTypes.hexahedron, CellTypes.voxel)
