from xml.etree import ElementTree
from typing import List

from ... import protocols
from ...mesh import merge, protocols as mesh_protocols

from ._vtu_reader import VTUReader
from ._vtp_reader import VTPReader
from ._reader_map import _VTKReader, _VTK_EXTENSION_TO_READER


class _PVTKReader:
    def __init__(self,
                 filename: str,
                 vtk_grid_type: str,
                 piece_reader: _VTKReader) -> None:
        self._grid_type = vtk_grid_type
        self._pieces = self._get_pieces(filename)
        self._piece_reader = piece_reader

    def read(self) -> protocols.FieldData:
        if not self._pieces:
            raise IOError("No pieces found in the given parallel vtk file")

        mesh_fields = self._read_piece(0)
        for piece_idx in range(len(self._pieces)):
            mesh_fields = merge(mesh_fields, self._read_piece(piece_idx))
        return mesh_fields

    def _get_pieces(self, filename: str) -> List[str]:
        xml_tree = ElementTree.parse(filename).getroot()
        grid = xml_tree.find(f"P{self._grid_type}")
        assert grid is not None
        return [c.attrib["Source"] for c in filter(lambda c: c.tag == "Piece", grid)]

    def _read_piece(self, idx: int) -> mesh_protocols.MeshFields:
        result = self._piece_reader(self._pieces[idx]).read()
        assert isinstance(result, mesh_protocols.MeshFields)
        return result


class PVTUReader(_PVTKReader):
    """Reads meshes from the VTK file format for parallel unstructured grids"""
    def __init__(self, filename: str) -> None:
        super().__init__(filename, "UnstructuredGrid", VTUReader)


class PVTPReader(_PVTKReader):
    """Reads meshes from the VTK file format for parallel polydata"""
    def __init__(self, filename: str) -> None:
        super().__init__(filename, "PolyData", VTPReader)


_VTK_EXTENSION_TO_READER[".pvtu"] = PVTUReader
_VTK_EXTENSION_TO_READER[".pvtp"] = PVTPReader
