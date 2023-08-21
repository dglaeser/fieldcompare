# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import List, Tuple
from itertools import accumulate
from operator import mul

import numpy as np

from ...mesh._cell_type import CellType
from ...mesh._cell_type_maps import _CELL_TYPE_INDEX_TO_STR, _CELL_TYPE_STR_TO_INDEX


def vtk_type_to_dtype(vtk_type: str) -> np.dtype:
    return np.dtype(_VTK_TYPE_TO_DTYPE[vtk_type])


def dtype_to_vtk_type(dtype) -> str:
    for name, _dtype in _VTK_TYPE_TO_DTYPE.items():
        if _dtype == dtype:
            return name
    raise RuntimeError("Could not determine vtk data type for" + str(dtype))


def vtk_cell_type_index_to_cell_type(vtk_cell_type: int) -> CellType:
    return CellType.from_name(_VTK_CELL_TYPE_TO_STR[vtk_cell_type])


def cell_type_to_vtk_cell_type_index(cell_type: CellType) -> int:
    return _VTK_CELL_TYPE_STR_TO_INDEX[cell_type.name]


def vtk_extents_to_cells_per_direction(extents: List[int]) -> Tuple[int, int, int]:
    num_expected_extent_entries = 6
    if len(extents) != num_expected_extent_entries:
        raise ValueError(f"Expected vtk extents to contain 6 integers, got {extents}")
    cells = (extents[1] - extents[0], extents[3] - extents[2], extents[5] - extents[4])
    if any(c < 0 for c in cells):
        raise ValueError(f"Number of cells must be >= 0 in all directions, got {cells}")
    return cells


def number_of_total_cells_from_cells_per_direction(cells: Tuple[int, int, int]) -> int:
    return list(accumulate(map(lambda c: max(c, 1), cells), mul, initial=1))[-1]


def number_of_total_points_from_cells_per_direction(cells: Tuple[int, int, int]) -> int:
    return list(accumulate(map(lambda c: c + 1, cells), mul, initial=1))[-1]


_VTK_SPACE_DIM = 3  # noqa: PLR2004


_VTK_TYPE_TO_DTYPE = {
    "Int8": np.int8,
    "Int16": np.int16,
    "Int32": np.int32,
    "Int64": np.int64,
    "UInt8": np.uint8,
    "UInt16": np.uint16,
    "UInt32": np.uint32,
    "UInt64": np.uint64,
    "Float32": np.float32,
    "Float64": np.float64,
}


# we actually use the same type indices (and names) as VTK
_VTK_CELL_TYPE_TO_STR = _CELL_TYPE_INDEX_TO_STR
_VTK_CELL_TYPE_STR_TO_INDEX = _CELL_TYPE_STR_TO_INDEX
