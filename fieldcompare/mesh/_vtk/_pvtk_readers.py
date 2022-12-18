from __future__ import annotations
from xml.etree import ElementTree
from typing import Optional, List, Protocol

from .._mesh_field_transformations import merge
from .. import protocols

from ._vtu_reader import VTUReader
from ._vtp_reader import VTPReader


class _Reader(Protocol):
    def read(self) -> protocols.MeshFields:
        ...


class _VTKReader(Protocol):
    def __call__(self, filename: str) -> _Reader:
        ...


class _PVTKReader:
    def __init__(self,
                 filename: str,
                 vtk_grid_type: str,
                 piece_reader: _VTKReader) -> None:
        self._grid_type = vtk_grid_type
        self._pieces = self._get_pieces(filename)
        self._piece_reader = piece_reader

    def read(self) -> protocols.MeshFields:
        mesh_fields: Optional[protocols.MeshFields] = None
        for piece in self._pieces:
            piece_fields = self._piece_reader(piece).read()
            mesh_fields = piece_fields if mesh_fields is None else merge(mesh_fields, piece_fields)
        assert mesh_fields is not None
        return mesh_fields

    def _get_pieces(self, filename: str) -> List[str]:
        xml_tree = ElementTree.parse(filename).getroot()
        grid = xml_tree.find(f"P{self._grid_type}")
        assert grid is not None
        return [c.attrib["Source"] for c in filter(lambda c: c.tag == "Piece", grid)]


class PVTUReader(_PVTKReader):
    def __init__(self, filename: str) -> None:
        super().__init__(filename, "UnstructuredGrid", VTUReader)


class PVTPReader(_PVTKReader):
    def __init__(self, filename: str) -> None:
        super().__init__(filename, "PolyData", VTPReader)
