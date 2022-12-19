"""Predefined cell type instances for the most commonly used cell types"""

from ._cell_type import CellType, _CELL_TYPE_STR_TO_INDEX

vertex = CellType(_CELL_TYPE_STR_TO_INDEX["VERTEX"])
line = CellType(_CELL_TYPE_STR_TO_INDEX["LINE"])
triangle = CellType(_CELL_TYPE_STR_TO_INDEX["TRIANGLE"])
polygon = CellType(_CELL_TYPE_STR_TO_INDEX["POLYGON"])
pixel = CellType(_CELL_TYPE_STR_TO_INDEX["PIXEL"])
quad = CellType(_CELL_TYPE_STR_TO_INDEX["QUAD"])
tetra = CellType(_CELL_TYPE_STR_TO_INDEX["TETRA"])
voxel = CellType(_CELL_TYPE_STR_TO_INDEX["VOXEL"])
hexahedron = CellType(_CELL_TYPE_STR_TO_INDEX["HEXAHEDRON"])
pyramid = CellType(_CELL_TYPE_STR_TO_INDEX["PYRAMID"])
