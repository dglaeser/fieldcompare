import numpy as np

from ...mesh._cell_type import CellType, cell_type_from_name
from ...mesh._cell_type import _CELL_TYPE_INDEX_TO_STR, _CELL_TYPE_STR_TO_INDEX


def vtk_type_to_dtype(vtk_type: str) -> np.dtype:
    return np.dtype(_VTK_TYPE_TO_DTYPE[vtk_type])


def vtk_cell_type_index_to_cell_type(vtk_cell_type: int) -> CellType:
    return cell_type_from_name(_VTK_CELL_TYPE_TO_STR[vtk_cell_type])


def cell_type_to_vtk_cell_type_index(cell_type: CellType) -> int:
    return _VTK_CELL_TYPE_STR_TO_INDEX[cell_type.name]


_VTK_TYPE_TO_DTYPE = {
    "Int8": np.int8, "Int16": np.int16, "Int32": np.int32, "Int64": np.int64,
    "UInt8": np.uint8, "UInt16": np.uint16, "UInt32": np.uint32, "UInt64": np.uint64,
    "Float32": np.float32, "Float64": np.float64
}


# we actually use the same type indices and names as VTK
_VTK_CELL_TYPE_TO_STR = _CELL_TYPE_INDEX_TO_STR
_VTK_CELL_TYPE_STR_TO_INDEX = _CELL_TYPE_STR_TO_INDEX
