from typing import Tuple

import numpy as np

from ...mesh import Mesh, CellType
from ._xml_reader import VTKXMLReader, CellTypeToCellIndices
from ._reader_map import _VTK_EXTENSION_TO_READER, _VTK_TYPE_TO_EXTENSION


class VTPReader(VTKXMLReader):
    """Reads meshes from the polydata variant of the VTK file formats"""

    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self._num_points = int(self._get_attribute("PolyData/Piece", "NumberOfPoints"))
        self._num_verts = int(self._get_attribute_or("PolyData/Piece", "NumberOfVerts", "0"))
        self._num_lines = int(self._get_attribute_or("PolyData/Piece", "NumberOfLines", "0"))
        self._num_polys = int(self._get_attribute_or("PolyData/Piece", "NumberOfPolys", "0"))
        self._num_strips = int(self._get_attribute_or("PolyData/Piece", "NumberOfStrips", "0"))
        for i, _ in enumerate(self._get_element("PolyData").findall("Piece")):
            if i > 0:
                raise NotImplementedError("VTP file with multiple pieces not supported (yet)")

    def _get_field_data_path(self) -> str:
        return "PolyData/Piece"

    def _make_mesh(self) -> Tuple[Mesh, CellTypeToCellIndices]:
        points = self._get_point_coordinates()
        cells = []
        sizes = []

        if self._num_verts > 0:
            cells.append((CellType.from_name("POLY_VERTEX"), self._get_connectivity("Verts")))
            sizes.append(self._num_verts)
        if self._num_lines > 0:
            cells.append((CellType.from_name("POLY_LINE"), self._get_connectivity("Lines")))
            sizes.append(self._num_lines)
        if self._num_polys > 0:
            cells.append((CellType.from_name("POLYGON"), self._get_connectivity("Polys")))
            sizes.append(self._num_polys)
        if self._num_strips > 0:
            cells.append((CellType.from_name("TRIANGLE_STRIP"), self._get_connectivity("Strips")))
            sizes.append(self._num_strips)

        offsets = np.cumsum(np.append(np.array([0], dtype=int), np.array(sizes, dtype=int)))
        cell_indices = [np.array(range(offsets[i], offsets[i] + sizes[i]), dtype=int) for i in range(len(sizes))]

        return Mesh(points=points, connectivity=((k, v) for k, v in cells)), {
            name: indices for (name, _), indices in zip(cells, cell_indices)
        }

    def _get_point_coordinates(self) -> np.ndarray:
        return self._get_data_array_values(self._get_element("PolyData/Piece/Points/DataArray")).reshape(
            self._num_points, 3
        )

    def _get_connectivity(self, poly_cell_type: str) -> np.ndarray:
        data_arrays = {
            elem.attrib["Name"]: elem
            for elem in self._get_element(f"PolyData/Piece/{poly_cell_type}")
            if elem.tag == "DataArray"
        }
        return self._get_cell_corners(
            self._make_data_array(data_arrays["connectivity"]), self._make_data_array(data_arrays["offsets"])
        )

    def _get_cell_corners(self, flat_corners: np.ndarray, offsets: np.ndarray) -> np.ndarray:
        num_cells = len(offsets)
        offsets = np.concatenate((np.array([0], dtype=offsets.dtype), offsets))

        def _get_corners(i: int) -> np.ndarray:
            return flat_corners[offsets[i] : offsets[i + 1]]

        try:  # homogeneous shape (yields faster processing with numpy algorithms)
            return np.array([_get_corners(i) for i in range(num_cells)], dtype=flat_corners.dtype)
        except ValueError:  # try with object dtype
            return np.array([_get_corners(i) for i in range(num_cells)], dtype="object")


_VTK_EXTENSION_TO_READER[".vtp"] = VTPReader
_VTK_TYPE_TO_EXTENSION["PolyData"] = ".vtp"
