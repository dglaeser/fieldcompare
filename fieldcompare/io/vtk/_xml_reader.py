from typing import Dict, Tuple, List, Literal, Optional
from abc import ABC, abstractmethod
from xml.etree import ElementTree

import numpy as np

from ...mesh import Mesh, MeshFields, CellType
from ._appendix import VTKXMLAppendix
from ._helpers import vtk_type_to_dtype
from ._encoders import Base64Encoder
from ._compressors import Compressor, NoCompressor, ZLIBCompressor, LZ4Compressor, LZMACompressor


CellTypeToCellIndices = Dict[CellType, np.ndarray]


class VTKXMLReader(ABC):
    """Abstract base class for VTK file readers in XML format"""

    def __init__(self, filename: str) -> None:
        self._appendix: Optional[VTKXMLAppendix] = None
        try:
            self._xml_element = ElementTree.parse(filename).getroot()
            elem = self._xml_element.find("AppendedData")
            if elem is not None and elem.text is not None:
                self._appendix = VTKXMLAppendix(
                    content=elem.text.strip("_ \n").encode(self._text_encoding), encoding=elem.attrib["encoding"]
                )
        except ElementTree.ParseError:
            content = open(filename, "rb").read()
            app_begin, app_end = _find_appendix_positions(content)
            self._appendix = VTKXMLAppendix(
                content=content[app_begin:app_end], encoding=_determine_encoding(content[app_begin - 100 :])
            )
            content_without_appendix = (
                content[:app_begin].decode(self._text_encoding).rsplit("<AppendedData")[0] + "</VTKFile>"
            )
            self._xml_element = ElementTree.fromstring(content_without_appendix)

        self._point_data_arrays = self._get_field_data_arrays("PointData")
        self._cell_data_arrays = self._get_field_data_arrays("CellData")

    def read(self) -> MeshFields:
        mesh_cell_indices_tuple = self._make_mesh()
        mesh: Mesh = mesh_cell_indices_tuple[0]
        cell_indices: CellTypeToCellIndices = mesh_cell_indices_tuple[1]

        num_points = len(mesh.points)

        def _make_point_data(elem: ElementTree.Element) -> np.ndarray:
            data = self._make_data_array(elem)
            assert len(data) == num_points
            return data

        num_cells = sum(len(mesh.connectivity(ct)) for ct in mesh.cell_types)

        def _make_cell_data(elem: ElementTree.Element) -> List[np.ndarray]:
            data = self._make_cell_data_array(elem, mesh, cell_indices)
            assert sum(len(sub_array) for sub_array in data) == num_cells
            return data

        return MeshFields(
            mesh=mesh,
            point_data={e.attrib["Name"]: _make_point_data(e) for e in self._point_data_arrays.values()},
            cell_data={e.attrib["Name"]: _make_cell_data(e) for e in self._cell_data_arrays.values()},
        )

    @abstractmethod
    def _make_mesh(self) -> Tuple[Mesh, CellTypeToCellIndices]:
        ...

    @abstractmethod
    def _get_field_data_path(self) -> str:
        ...

    def _make_cell_data_array(
        self, element: ElementTree.Element, mesh: Mesh, index_map: CellTypeToCellIndices
    ) -> List[np.ndarray]:
        result: List[np.ndarray] = []
        entire_data_array = self._make_data_array(element)
        for cell_type in mesh.cell_types:
            result.append(entire_data_array[index_map[cell_type]])
        return result

    def _make_data_array(self, xml_element: ElementTree.Element) -> np.ndarray:
        return self._reshape_data_array_values(xml_element, self._get_data_array_values(xml_element))

    def _reshape_data_array_values(self, xml_element: ElementTree.Element, values: np.ndarray) -> np.ndarray:
        ncomps = int(xml_element.attrib.get("NumberOfComponents", 1))
        return values if ncomps <= 1 else values.reshape(int(len(values) / ncomps), ncomps)

    def _get_attribute(self, path: str, key: str) -> str:
        return self._get_attribute_from(self._get_element(path), key)

    def _get_attribute_or(self, path: str, key: str, default: str) -> str:
        elem = self._xml_element.find(path)
        if elem is None:
            return default
        return elem.attrib[key] if key in elem.attrib else default

    def _get_attribute_from(self, elem: ElementTree.Element, key: str) -> str:
        if key not in elem.attrib:
            raise KeyError(f"Attribute '{key}' not in xml element '{elem.tag}'")
        return elem.attrib[key]

    def _get_element(self, path: str) -> ElementTree.Element:
        elem = self._xml_element.find(path)
        if elem is not None:
            return elem
        raise ValueError("Path not found in vtk file")

    def _get_field_data_arrays(self, section: str) -> Dict[str, ElementTree.Element]:
        path = f"{self._get_field_data_path()}/{section}"
        try:
            xml_element = self._get_element(path)
        except ValueError:
            return {}
        return {data_array.attrib["Name"]: data_array for data_array in xml_element}

    @property
    def _text_encoding(self) -> str:
        return "ascii"

    @property
    def _byte_order(self) -> Literal["<", ">"]:
        return "<" if self._get_attribute(".", "byte_order") == "LittleEndian" else ">"

    @property
    def _header_type(self) -> np.dtype:
        """Return the header type used in the VTK file"""
        return vtk_type_to_dtype(self._xml_element.attrib.get("header_type", "UInt32")).newbyteorder(self._byte_order)

    @property
    def _compressor(self) -> Compressor:
        """Return the compression method used in the VTK file"""
        comp = self._xml_element.attrib.get("compressor")
        if comp is None:
            return NoCompressor(header_type=self._header_type)
        if comp == "vtkZLibDataCompressor":
            return ZLIBCompressor(header_type=self._header_type)
        if comp == "vtkLZMADataCompressor":
            return LZMACompressor(header_type=self._header_type)
        if comp == "vtkLZ4DataCompressor":
            return LZ4Compressor(header_type=self._header_type)
        raise NotImplementedError(f"Unsupported compressor type '{comp}'")

    @property
    def _endianness(self) -> str:
        """Return the endianness of the data in the VTK file"""
        return self._xml_element.attrib["byte_order"]

    def _get_data_array_values(self, xml: ElementTree.Element) -> np.ndarray:
        if xml.attrib["format"] == "ascii":
            return self._get_inline_ascii_data_array_values(xml)
        elif xml.attrib["format"] == "binary":
            return self._get_inline_binary_data_array_values(xml)
        else:
            return self._get_appended_data_array_values(xml)

    def _get_inline_ascii_data_array_values(self, xml: ElementTree.Element) -> np.ndarray:
        assert xml.text is not None
        return np.fromstring(xml.text.strip("\n").strip(), dtype=vtk_type_to_dtype(xml.attrib["type"]), sep=" ")

    def _get_inline_binary_data_array_values(self, xml: ElementTree.Element) -> np.ndarray:
        assert xml.text is not None
        return np.frombuffer(
            self._compressor.get_decompressed_data(xml.text.strip().strip("\n").encode(), Base64Encoder()),
            vtk_type_to_dtype(xml.attrib["type"]).newbyteorder(self._byte_order),
        )

    def _get_appended_data_array_values(self, xml: ElementTree.Element) -> np.ndarray:
        assert self._appendix is not None
        return np.frombuffer(
            self._compressor.get_decompressed_data(
                self._appendix.get(int(xml.attrib["offset"].strip())), self._appendix.encoder
            ),
            vtk_type_to_dtype(xml.attrib["type"]).newbyteorder(self._byte_order),
        )


def _find_appendix_positions(content: bytes) -> Tuple[int, int]:
    start_pos = content.find(b"<AppendedData")
    assert not _is_end(start_pos)
    positions = _find_enclosed_content_range(content, start_pos, b"<", b">")
    assert positions is not None
    app_begin_pos = content.find(b"_", positions[1] + len(b">"))
    assert not _is_end(app_begin_pos)
    app_end_pos = content.find(b"</AppendedData>")
    assert not _is_end(app_end_pos)
    return app_begin_pos + len(b"_"), app_end_pos


def _determine_encoding(content: bytes) -> str:
    pos = content.rfind(b"<AppendedData")
    pos = content.find(b"encoding", pos)
    encoding_range = _find_enclosed_content_range(content, pos, b'"', b'"')
    assert encoding_range is not None
    return str(content[encoding_range[0] : encoding_range[1]].decode("ascii"))


def _find_enclosed_content_range(
    content: bytes, start_pos: int, open_char: bytes, close_char: bytes
) -> Optional[Tuple[int, int]]:
    cur_pos = content.find(open_char, start_pos)
    start_pos = cur_pos + 1
    if _is_end(cur_pos):
        return None

    if open_char == close_char:
        end_pos = content.find(close_char, start_pos)
        return None if end_pos is None else (start_pos, end_pos)

    open_count = 1
    close_count = 0

    while not _is_end(cur_pos):
        next_open_pos = content.find(open_char, cur_pos + 1)
        next_close_pos = content.find(close_char, cur_pos + 1)
        if not _is_end(next_close_pos):
            close_count += 1
            if open_count == close_count and (_is_end(next_open_pos) or next_close_pos < next_open_pos):
                return start_pos, next_close_pos
            elif not _is_end(next_open_pos):
                open_count += 1
        cur_pos = max(next_open_pos, next_close_pos)
    return None


def _is_end(position: int) -> bool:
    return position == -1
