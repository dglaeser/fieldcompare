from typing import Tuple, Dict
from xml.etree import ElementTree

import numpy as np

from .._mesh import Mesh
from ._helpers import vtk_cell_type_to_str
from ._xml_reader import VTKXMLReader, CellTypeToCellIndices


class VTUReader(VTKXMLReader):
    """Mesh file reader implementation for the VTU variant of the VTK file formats"""
    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self._num_cells = int(self._get_attribute("UnstructuredGrid/Piece", "NumberOfCells"))
        self._num_points = int(self._get_attribute("UnstructuredGrid/Piece", "NumberOfPoints"))
        self._mesh_data_arrays = self._get_mesh_data_arrays()
        for i, _ in enumerate(self._get_element("UnstructuredGrid").findall("Piece")):
            if i > 0:
                raise NotImplementedError("VTU file with multiple pieces")

    def _get_field_data_path(self) -> str:
        return "UnstructuredGrid/Piece"

    def _make_mesh(self) -> Tuple[Mesh, CellTypeToCellIndices]:
        points = self._get_data_array_values(self._mesh_data_arrays["points"])
        corners = self._get_data_array_values(self._mesh_data_arrays["connectivity"])
        offsets = self._get_data_array_values(self._mesh_data_arrays["offsets"])
        types = self._get_data_array_values(self._mesh_data_arrays["types"])
        ocurring_types = np.unique(types)

        assert len(points) == self._num_points*3
        assert len(offsets) == self._num_cells
        assert len(types) == self._num_cells

        # prepend zero offset to access offset for cell with its index directly
        offsets = np.append(np.array([0], dtype=offsets.dtype), offsets)

        def _num_corners(cell_type_idx) -> int:
            return offsets[cell_type_idx+1] - offsets[cell_type_idx]

        def _cell_type_indices(cell_type) -> np.ndarray:
            indices = np.equal(types, cell_type).nonzero()
            assert len(indices) == 1
            return indices[0]

        def _cell_type_corners_array(cell_type) -> np.ndarray:
            indices = _cell_type_indices(cell_type)
            num_cells_with_given_type = len(indices)
            num_cell_type_corners = _num_corners(indices[0])
            assert num_cells_with_given_type > 0
            return corners[
                np.linspace(
                    offsets[indices],
                    offsets[indices]+num_cell_type_corners,
                    num=num_cell_type_corners,
                    endpoint=False,
                    axis=1,
                    dtype=indices.dtype
                )
            ]

        return Mesh(
            points=points.reshape(int(len(points)/3), 3),
            connectivity=(
                (vtk_cell_type_to_str(t), _cell_type_corners_array(t))
                for t in ocurring_types
            )
        ), {vtk_cell_type_to_str(t): _cell_type_indices(t) for t in ocurring_types}

    def _get_mesh_data_arrays(self) -> Dict[str, ElementTree.Element]:
        return {
            **{"points": self._get_element("UnstructuredGrid/Piece/Points/DataArray")},
            **{
                data_array.attrib["Name"]: data_array
                for data_array in self._get_element("UnstructuredGrid/Piece/Cells")
            }
        }
