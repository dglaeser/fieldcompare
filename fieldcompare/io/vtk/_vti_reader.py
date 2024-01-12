# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import numpy as np

from ...mesh import ImageMesh
from ...mesh._structured_mesh import standard_basis

from ._xml_reader import VTKXMLStructuredReader, CellTypeToCellIndices
from ._reader_map import _VTK_EXTENSION_TO_READER, _VTK_TYPE_TO_EXTENSION
from ._helpers import (
    number_of_total_cells_from_cells_per_direction,
    number_of_total_points_from_cells_per_direction,
)


class VTIReader(VTKXMLStructuredReader):
    """Reads meshes from the image grid variant of the VTK file formats"""

    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self._origin = [float(x) for x in self._get_attribute("ImageData", "Origin").split()]
        self._spacing = [float(dx) for dx in self._get_attribute("ImageData", "Spacing").split()]
        self._num_cells = number_of_total_cells_from_cells_per_direction(self._cells)
        self._num_points = number_of_total_points_from_cells_per_direction(self._cells)
        self._basis = standard_basis()
        if self._has_attribute("ImageData", "Direction"):
            vtk_basis = [float(dx) for dx in self._get_attribute("ImageData", "Direction").split()]
            for i in range(len(self._basis)):
                self._basis[i] = vtk_basis[i * 3 : (i + 1) * 3]

    @property
    def origin(self) -> list[float]:
        return self._origin

    @property
    def spacing(self) -> list[float]:
        return self._spacing

    def _get_field_data_path(self) -> str:
        return "ImageData/Piece"

    def _make_mesh(self) -> tuple[ImageMesh, CellTypeToCellIndices]:
        mesh = ImageMesh(
            extents=(self._cells[0], self._cells[1], self._cells[2]),
            origin=(self._origin[0], self._origin[1], self._origin[2]),
            spacing=(self._spacing[0], self._spacing[1], self._spacing[2]),
            basis=np.copy(self._basis),
        )
        cell_types = list(mesh.cell_types)
        assert len(cell_types) == 1
        return mesh, {cell_types[0]: np.array(range(self._num_cells))}


_VTK_EXTENSION_TO_READER[".vti"] = VTIReader
_VTK_TYPE_TO_EXTENSION["ImageData"] = ".vti"
