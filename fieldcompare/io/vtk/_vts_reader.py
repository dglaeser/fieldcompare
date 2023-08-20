# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations
from itertools import accumulate
from operator import mul

import numpy as np

from ...mesh import Mesh, CellTypes
from ._xml_reader import VTKXMLReader, CellTypeToCellIndices
from ._reader_map import _VTK_EXTENSION_TO_READER, _VTK_TYPE_TO_EXTENSION


class VTSReader(VTKXMLReader):
    """Reads meshes from the structured grid variant of the VTK file formats"""

    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        raw_extents = [int(e) for e in self._get_attribute("StructuredGrid/Piece", "Extent").split()]
        self._extents = [(raw_extents[i * 2], raw_extents[i * 2 + 1]) for i in range(3)]
        self._cells = list(map(lambda i: self._extents[i][1] - self._extents[i][0], range(3)))
        self._num_cells = list(accumulate(map(lambda c: max(c, 1), self._cells), mul, initial=1))[-1]
        self._num_points = list(accumulate(map(lambda c: c + 1, self._cells), mul, initial=1))[-1]

    def _get_field_data_path(self) -> str:
        return "StructuredGrid/Piece"

    def _make_mesh(self) -> tuple[Mesh, CellTypeToCellIndices]:
        nonzero_extents = [c for c in self._cells if c > 0]
        dimension = sum(map(lambda e: 1 if e > 0 else 0, nonzero_extents))

        cells = []
        points = self._get_data_array_values(self._get_element("StructuredGrid/Piece/Points/DataArray")).reshape(
            self._num_points, 3
        )

        if dimension == 1:  # noqa: PLR2004
            cells = [[i, i + 1] for i in range(self._num_cells)]
        elif dimension == 2:  # noqa: PLR2004
            xoffset = nonzero_extents[0] + 1
            for j in range(nonzero_extents[1]):
                for i in range(nonzero_extents[0]):
                    p0 = j * xoffset + i
                    cells.append([p0, p0 + 1, p0 + xoffset + 1, p0 + xoffset])
        elif dimension == 3:  # noqa: PLR2004
            xoffset = nonzero_extents[0] + 1
            xyoffset = xoffset * (nonzero_extents[1] + 1)
            for k in range(nonzero_extents[2]):
                for j in range(nonzero_extents[1]):
                    for i in range(nonzero_extents[0]):
                        p0 = k * xyoffset + j * xoffset + i
                        base_quad = [p0, p0 + 1, p0 + xoffset + 1, p0 + xoffset]
                        cells.append(base_quad + [i + xyoffset for i in base_quad])
        else:
            raise ValueError("Dimension must be > 0 and < 3")

        return Mesh(points=points, connectivity=[(CellTypes.quad, cells)]), {
            CellTypes.quad: np.array(range(self._num_cells))
        }


_VTK_EXTENSION_TO_READER[".vts"] = VTSReader
_VTK_TYPE_TO_EXTENSION["StructuredGrid"] = ".vts"
