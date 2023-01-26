# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

from os.path import splitext, exists, join, dirname, isabs
from xml.etree import ElementTree

from ... import protocols, FieldDataSequence
from ._reader_map import _VTK_EXTENSION_TO_READER, _VTK_TYPE_TO_EXTENSION


class PVDReader:
    """Reads VTK mesh sequences from .pvd files"""

    class _PVDSequenceSource:
        def __init__(self, filename: str) -> None:
            collection = ElementTree.parse(filename).find("Collection")
            assert collection is not None
            self._pieces = [dataset.attrib["file"] for dataset in collection if dataset.tag == "DataSet"]
            self._step_idx = 0
            self._dirname = dirname(filename)

        def reset(self) -> None:
            self._step_idx = 0

        def step(self) -> bool:
            self._step_idx += 1
            return self._step_idx < len(self._pieces)

        def get(self) -> protocols.FieldData:
            filename = self._pieces[self._step_idx]
            if not exists(filename) and not isabs(filename) and exists(join(self._dirname, filename)):
                filename = join(self._dirname, filename)

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
        return FieldDataSequence(source=self._PVDSequenceSource(self._filename))


# register this reader in the map
_VTK_EXTENSION_TO_READER[".pvd"] = PVDReader
_VTK_TYPE_TO_EXTENSION["Collection"] = ".pvd"
