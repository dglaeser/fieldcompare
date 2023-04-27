# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import Union, Sequence, Iterable, Tuple, Optional
from xml.etree.ElementTree import ElementTree, SubElement, Element as XMLElement

try:  # indent came in 3.9
    from xml.etree.ElementTree import indent  # type: ignore
except ImportError:

    def indent(tree: Union[XMLElement, ElementTree], space: str = ..., level: int = ...) -> None:
        pass


from itertools import accumulate
from base64 import b64encode
from sys import byteorder
from numpy import uint64

from ...mesh import CellType
from ...mesh import protocols
from ...mesh._mesh_fields import remove_cell_type_suffix
from ..._numpy_utils import Array, make_array, concatenate, flatten, to_bytes

from ._helpers import cell_type_to_vtk_cell_type_index, dtype_to_vtk_type


class VTUWriter:
    def __init__(self, fields: protocols.MeshFields) -> None:
        self._fields = fields

    def write(self, filename: str) -> None:
        vtkfile = XMLElement(
            "VTKFile",
            attrib={
                "type": "UnstructuredGrid",
                "version": "1.0",
                "header_type": "UInt64",
                "byte_order": ("LittleEndian" if byteorder == "little" else "BigEndian"),
            },
        )
        grid = SubElement(vtkfile, "UnstructuredGrid")
        piece = SubElement(
            grid, "Piece", attrib={"NumberOfPoints": str(self._num_points), "NumberOfCells": str(self._num_cells)}
        )

        point_data = SubElement(piece, "PointData")
        for pfield in self._fields.point_fields:
            self._make_data_array_element(point_data, pfield.name, pfield.values)
        cell_data = SubElement(piece, "CellData")
        for name, values in self._cell_fields():
            self._make_data_array_element(cell_data, name, values)

        points = SubElement(piece, "Points")
        self._make_data_array_element(points, "Coordinates", values=[self._make_3d(p) for p in self._points()])

        cells = SubElement(piece, "Cells")
        self._make_data_array_element(
            cells, "connectivity", values=[index for (_, corners) in self._cells() for index in corners]
        )
        self._make_data_array_element(
            cells, "offsets", values=[v for v in accumulate(len(corners) for (_, corners) in self._cells())]
        )
        self._make_data_array_element(
            cells, "types", values=[cell_type_to_vtk_cell_type_index(ct) for (ct, _) in self._cells()]
        )

        tree = ElementTree(vtkfile)
        indent(tree, space="  ", level=0)
        tree.write(f"{filename}.vtu", xml_declaration=False, encoding="ascii")

    def _make_data_array_element(self, parent: XMLElement, name: str, values: Union[Sequence, Array]) -> XMLElement:
        values = make_array(values)
        ncomps = self._array_num_components(values)
        elem = SubElement(
            parent,
            "DataArray",
            attrib={
                "Name": name,
                "type": dtype_to_vtk_type(values.dtype),
                "format": "binary",
                "NumberOfComponents": str(ncomps),
            },
        )
        num_bytes = len(values) * ncomps * values.itemsize
        elem.text = str(
            b64encode(to_bytes(make_array([uint64(num_bytes)])) + to_bytes(flatten(values))), encoding="ascii"
        )
        return elem

    @property
    def _num_cells(self) -> int:
        num_cells = 0
        for ct in self._fields.domain.cell_types:
            num_cells += len(self._fields.domain.connectivity(ct))
        return num_cells

    @property
    def _num_points(self) -> int:
        return len(self._fields.domain.points)

    def _cells(self) -> Iterable[Tuple[CellType, Array]]:
        return (
            (ct, connectivity)
            for ct in self._fields.domain.cell_types
            for connectivity in self._fields.domain.connectivity(ct)
        )

    def _cell_fields(self) -> Iterable[Tuple[str, Array]]:
        names = set(remove_cell_type_suffix(ct, field.name) for field, ct in self._fields.cell_fields_types)
        return ((name, self._get_cell_field_values(name)) for name in names)

    def _get_cell_field_values(self, name: str) -> Array:
        values: Optional[Array] = None
        for ct in self._fields.domain.cell_types:
            for field, fct in self._fields.cell_fields_types:
                if fct == ct and remove_cell_type_suffix(fct, field.name) == name:
                    values = concatenate([values, field.values] if values is not None else [field.values])
        assert isinstance(values, Array)
        return values

    def _points(self) -> Iterable:
        return self._fields.domain.points

    def _make_3d(self, point: Array) -> Array:
        if len(point) == 3:
            return point
        result: Array = Array(shape=(3,))
        result.fill(0.0)
        for i in range(len(point)):
            result[i] = point[i]
        return result

    def _array_num_components(self, values: Array) -> int:
        assert len(values) > 0
        result = self._num_components(values[0])
        return result

    def _num_components(self, array_entry) -> int:
        if not isinstance(array_entry, Iterable):
            return 1
        return list(accumulate((self._num_components(entry) for entry in array_entry)))[-1]
