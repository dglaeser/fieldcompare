# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import numpy as np

from ...mesh import StructuredMesh, CellTypes
from ._xml_reader import VTKXMLReader, CellTypeToCellIndices
from ._reader_map import _VTK_EXTENSION_TO_READER, _VTK_TYPE_TO_EXTENSION
from ._helpers import (
    vtk_extents_to_cells_per_direction,
    number_of_total_cells_from_cells_per_direction,
    number_of_total_points_from_cells_per_direction,
)


class VTSReader(VTKXMLReader):
    """Reads meshes from the structured grid variant of the VTK file formats"""

    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self._cells = vtk_extents_to_cells_per_direction(
            [int(e) for e in self._get_attribute("StructuredGrid/Piece", "Extent").split()]
        )
        self._num_cells = number_of_total_cells_from_cells_per_direction(self._cells)
        self._num_points = number_of_total_points_from_cells_per_direction(self._cells)

    def _get_field_data_path(self) -> str:
        return "StructuredGrid/Piece"

    def _make_mesh(self) -> tuple[StructuredMesh, CellTypeToCellIndices]:
        points = self._get_data_array_values(self._get_element("StructuredGrid/Piece/Points/DataArray")).reshape(
            self._num_points, 3
        )
        return StructuredMesh((self._cells[0], self._cells[1], self._cells[2]), points), {
            CellTypes.quad: np.arange(self._num_cells)
        }


_VTK_EXTENSION_TO_READER[".vts"] = VTSReader
_VTK_TYPE_TO_EXTENSION["StructuredGrid"] = ".vts"
