"""I/O facilities for reading field data from VTK files"""

from os.path import splitext
from typing import Union

from .. import protocols

from ._vtp_reader import VTPReader
from ._vtu_reader import VTUReader
from ._pvtk_readers import PVTPReader, PVTUReader
from ._pvd_reader import PVDReader

from ._reader_map import _VTK_EXTENSION_TO_READER


def read(filename: str) -> Union[protocols.FieldData, protocols.FieldDataSequence]:
    """Read field data from the given VTK file"""
    ext = splitext(filename)[1]
    if ext not in _VTK_EXTENSION_TO_READER:
        raise IOError(f"Unsupported VTK file extension '{ext}'")
    return _VTK_EXTENSION_TO_READER[ext](filename).read()


def is_supported(filename: str) -> bool:
    """Return true if the given file can be read by the VTK readers"""
    return splitext(filename)[1] in _VTK_EXTENSION_TO_READER
