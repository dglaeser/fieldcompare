from __future__ import annotations
from os.path import splitext
from xml.etree import ElementTree
from typing import Dict

from ..._field_sequence import FieldDataSequence

from .._mesh_fields import MeshFields
from .. import protocols

from ._vtu_reader import VTUReader
from ._vtp_reader import VTPReader
from ._pvtk_readers import PVTUReader, PVTPReader, _VTKReader


_VTK_MESH_EXTENSIONS_TO_READER: Dict[str, _VTKReader] = {
    ".vtu": VTUReader,
    ".vtp": VTPReader,
    ".pvtu": PVTUReader,
    ".pvtp": PVTPReader
}


def read(filename: str) -> protocols.MeshFields:
    """Read mesh fields from the given VTK file"""
    ext = splitext(filename)[1]
    if ext not in _VTK_MESH_EXTENSIONS_TO_READER:
        raise IOError(f"Unsupported VTK file extension '{ext}'")
    return _VTK_MESH_EXTENSIONS_TO_READER[ext](filename).read()


def read_sequence(filename: str) -> FieldDataSequence:
    """Read a sequence from a VTK file"""
    return FieldDataSequence(source=_PVDSequenceSource(filename))


def is_supported(filename: str) -> bool:
    """Return true if the given VTK file is supported"""
    return splitext(filename)[1] in _VTK_MESH_EXTENSIONS_TO_READER


def is_supported_sequence(filename: str) -> bool:
    """Return true if the given VTK sequence file is supported"""
    return splitext(filename)[1] == ".pvd"


class _PVDSequenceSource:
    def __init__(self, filename: str) -> None:
        collection = ElementTree.parse(filename).find("Collection")
        assert collection is not None
        self._pieces = [
            dataset.attrib["file"]
            for dataset in collection
            if dataset.tag == "DataSet"
        ]
        self._step_idx = 0

    def reset(self) -> None:
        self._step_idx = 0

    def step(self) -> bool:
        self._step_idx += 1
        return self._step_idx < len(self._pieces)

    def get(self) -> protocols.MeshFields:
        filename = self._pieces[self._step_idx]
        ext = splitext(filename)[1]
        return _VTK_MESH_EXTENSIONS_TO_READER[ext](filename).read()

    @property
    def number_of_steps(self) -> int:
        return len(self._pieces)
