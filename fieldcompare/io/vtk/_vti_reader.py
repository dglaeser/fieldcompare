# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import numpy as np

from ..._numpy_utils import make_zeros
from ...mesh import StructuredMesh, CellTypes
from ._xml_reader import VTKXMLReader, CellTypeToCellIndices
from ._reader_map import _VTK_EXTENSION_TO_READER, _VTK_TYPE_TO_EXTENSION
from ._helpers import (
    vtk_extents_to_cells_per_direction,
    number_of_total_cells_from_cells_per_direction,
    number_of_total_points_from_cells_per_direction,
)


class VTIReader(VTKXMLReader):
    """Reads meshes from the image grid variant of the VTK file formats"""

    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self._cells = vtk_extents_to_cells_per_direction(
            [int(e) for e in self._get_attribute("ImageData/Piece", "Extent").split()]
        )
        self._origin = [float(x) for x in self._get_attribute("ImageData", "Origin").split()]
        self._spacing = [float(dx) for dx in self._get_attribute("ImageData", "Spacing").split()]
        self._num_cells = number_of_total_cells_from_cells_per_direction(self._cells)
        self._num_points = number_of_total_points_from_cells_per_direction(self._cells)

    def _get_field_data_path(self) -> str:
        return "ImageData/Piece"

    def _make_mesh(self) -> tuple[StructuredMesh, CellTypeToCellIndices]:
        i = 0
        points = make_zeros(shape=(self._num_points, 3))
        for iz in range(self._cells[2] + 1):
            for iy in range(self._cells[1] + 1):
                for ix in range(self._cells[0] + 1):
                    points[i] = [
                        self._origin[0] + self._spacing[0] * ix,
                        self._origin[1] + self._spacing[1] * iy,
                        self._origin[2] + self._spacing[2] * iz,
                    ]
                    i += 1
        return StructuredMesh((self._cells[0], self._cells[1], self._cells[2]), points), {
            CellTypes.quad: np.array(range(self._num_cells))
        }


_VTK_EXTENSION_TO_READER[".vti"] = VTIReader
_VTK_TYPE_TO_EXTENSION["ImageData"] = ".vti"
