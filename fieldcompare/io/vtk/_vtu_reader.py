# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations
from xml.etree import ElementTree

import numpy as np

from ...mesh import Mesh
from ._helpers import vtk_cell_type_index_to_cell_type
from ._xml_reader import VTKXMLReader, CellTypeToCellIndices
from ._reader_map import _VTK_EXTENSION_TO_READER, _VTK_TYPE_TO_EXTENSION


class VTUReader(VTKXMLReader):
    """Reads meshes from the unstructured grid variant of the VTK file formats"""

    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self._num_cells = int(self._get_attribute("UnstructuredGrid/Piece", "NumberOfCells"))
        self._num_points = int(self._get_attribute("UnstructuredGrid/Piece", "NumberOfPoints"))
        self._mesh_data_arrays = self._get_mesh_data_arrays()
        for i, _ in enumerate(self._get_element("UnstructuredGrid").findall("Piece")):
            if i > 0:
                raise NotImplementedError("VTU files with multiple pieces not supported (yet)")

    def _get_field_data_path(self) -> str:
        return "UnstructuredGrid/Piece"

    def _make_mesh(self) -> tuple[Mesh, CellTypeToCellIndices]:
        points = self._get_data_array_values(self._mesh_data_arrays["points"])
        corners = self._get_data_array_values(self._mesh_data_arrays["connectivity"])
        offsets = self._get_data_array_values(self._mesh_data_arrays["offsets"])
        types = self._get_data_array_values(self._mesh_data_arrays["types"])
        ocurring_types = np.unique(types)

        assert len(points) == self._num_points * 3
        assert len(offsets) == self._num_cells
        assert len(types) == self._num_cells

        # prepend zero offset to access offset for cell with its index directly
        offsets = np.append(np.array([0], dtype=offsets.dtype), offsets)

        def _num_corners(cell_type_idx) -> int:
            return offsets[cell_type_idx + 1] - offsets[cell_type_idx]

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
                    offsets[indices] + num_cell_type_corners,
                    num=num_cell_type_corners,
                    endpoint=False,
                    axis=1,
                    dtype=indices.dtype,
                )
            ]

        return Mesh(
            points=points.reshape(int(len(points) / 3), 3),
            connectivity=((vtk_cell_type_index_to_cell_type(t), _cell_type_corners_array(t)) for t in ocurring_types),
        ), {vtk_cell_type_index_to_cell_type(t): _cell_type_indices(t) for t in ocurring_types}

    def _get_mesh_data_arrays(self) -> dict[str, ElementTree.Element]:
        return {
            **{"points": self._get_element("UnstructuredGrid/Piece/Points/DataArray")},
            **{
                data_array.attrib["Name"]: data_array
                for data_array in self._get_element("UnstructuredGrid/Piece/Cells")
            },
        }


_VTK_EXTENSION_TO_READER[".vtu"] = VTUReader
_VTK_TYPE_TO_EXTENSION["UnstructuredGrid"] = ".vtu"
