# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import numpy as np
from xml.etree import ElementTree

from ...mesh import RectilinearMesh
from ._xml_reader import VTKXMLStructuredReader, CellTypeToCellIndices
from ._reader_map import _VTK_EXTENSION_TO_READER, _VTK_TYPE_TO_EXTENSION
from ._helpers import (
    _VTK_SPACE_DIM,
    number_of_total_cells_from_cells_per_direction,
    number_of_total_points_from_cells_per_direction,
)


class VTRReader(VTKXMLStructuredReader):
    """Reads meshes from the rectilinear grid variant of the VTK file formats"""

    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self._num_cells = number_of_total_cells_from_cells_per_direction(self._cells)
        self._num_points = number_of_total_points_from_cells_per_direction(self._cells)
        self._ordinate_elements = self._get_elements("RectilinearGrid/Piece/Coordinates/DataArray")
        if len(self._ordinate_elements) != _VTK_SPACE_DIM:
            raise IOError(f"Expected three coordinate elements, found {len(self._ordinate_elements)}")

    def ordinates(self, axis: int) -> np.ndarray:
        """Return the ordinates of the mesh along the given axis"""
        assert 0 <= axis <= _VTK_SPACE_DIM
        return self._get_ordinates(self._ordinate_elements[axis])

    def _get_field_data_path(self) -> str:
        return "RectilinearGrid/Piece"

    def _make_mesh(self) -> tuple[RectilinearMesh, CellTypeToCellIndices]:
        mesh = RectilinearMesh(
            (self._cells[0], self._cells[1], self._cells[2]),
            (self.ordinates(0), self.ordinates(1), self.ordinates(2)),
        )
        types = list(mesh.cell_types)
        assert len(types) == 1
        return mesh, {types[0]: np.arange(self._num_cells)}

    def _get_ordinates(self, element: ElementTree.Element) -> np.ndarray:
        raw_ordinates = self._get_data_array_values(element)
        return np.array([0.0]) if raw_ordinates.shape[0] == 0 else raw_ordinates


_VTK_EXTENSION_TO_READER[".vtr"] = VTRReader
_VTK_TYPE_TO_EXTENSION["RectilinearGrid"] = ".vtr"
