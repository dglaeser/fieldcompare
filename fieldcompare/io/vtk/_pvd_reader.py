from os.path import splitext
from xml.etree import ElementTree

from ... import protocols, FieldDataSequence
from ._reader_map import _VTK_EXTENSION_TO_READER


class PVDReader:
    """Reads VTK mesh sequences from .pvd files"""

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

        def get(self) -> protocols.FieldData:
            filename = self._pieces[self._step_idx]
            ext = splitext(filename)[1]
            fields = _VTK_EXTENSION_TO_READER[ext](filename).read()
            assert isinstance(fields, protocols.FieldData)
            return fields

        @property
        def number_of_steps(self) -> int:
            return len(self._pieces)

    def __init__(self, filename: str) -> None:
        """Construct a reader from the given file"""
        self._filename = filename

    def read(self) -> protocols.FieldDataSequence:
        """Return the sequence read from the file given upon construction"""
        return FieldDataSequence(
            source=self._PVDSequenceSource(self._filename)
        )


# register this reader in the map
_VTK_EXTENSION_TO_READER[".pvd"] = PVDReader
