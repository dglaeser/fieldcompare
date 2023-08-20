# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations
from itertools import accumulate
from operator import mul

import numpy as np

from ...mesh import StructuredMesh, CellTypes
from ._xml_reader import VTKXMLReader, CellTypeToCellIndices
from ._reader_map import _VTK_EXTENSION_TO_READER, _VTK_TYPE_TO_EXTENSION


_VTK_SPACE_DIM = 3


class VTSReader(VTKXMLReader):
    """Reads meshes from the structured grid variant of the VTK file formats"""

    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        raw_extents = [int(e) for e in self._get_attribute("StructuredGrid/Piece", "Extent").split()]
        self._extents = [(raw_extents[i * 2], raw_extents[i * 2 + 1]) for i in range(3)]
        self._cells = list(map(lambda i: self._extents[i][1] - self._extents[i][0], range(3)))
        self._num_cells = list(accumulate(map(lambda c: max(c, 1), self._cells), mul, initial=1))[-1]
        self._num_points = list(accumulate(map(lambda c: c + 1, self._cells), mul, initial=1))[-1]
        if len(self._cells) != _VTK_SPACE_DIM:
            raise ValueError(f"Expected three-dimensional extents, read {self._cells}")

    def _get_field_data_path(self) -> str:
        return "StructuredGrid/Piece"

    def _make_mesh(self) -> tuple[StructuredMesh, CellTypeToCellIndices]:
        points = self._get_data_array_values(self._get_element("StructuredGrid/Piece/Points/DataArray")).reshape(
            self._num_points, 3
        )
        return StructuredMesh((self._cells[0], self._cells[1], self._cells[2]), points), {
            CellTypes.quad: np.array(range(self._num_cells))
        }


_VTK_EXTENSION_TO_READER[".vts"] = VTSReader
_VTK_TYPE_TO_EXTENSION["StructuredGrid"] = ".vts"
