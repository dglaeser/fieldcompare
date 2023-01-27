# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""I/O facilities for reading field data from VTK files"""

from os.path import splitext
from typing import Union, Optional

from .. import protocols

from ._vtp_reader import VTPReader
from ._vtu_reader import VTUReader
from ._pvtk_readers import PVTPReader, PVTUReader
from ._pvd_reader import PVDReader

from ._reader_map import _VTK_EXTENSION_TO_READER, _VTK_TYPE_TO_EXTENSION


def read(filename: str) -> Union[protocols.FieldData, protocols.FieldDataSequence]:
    """Read field data from the given VTK file"""
    ext = _get_vtk_flavor_extension(filename)
    if ext is None:
        raise IOError(f"Could not determine VTK flavor of '{filename}'")
    return _VTK_EXTENSION_TO_READER[ext](filename).read()


def is_supported(filename: str) -> bool:
    """Return true if the given file can be read by the VTK readers"""
    return _get_vtk_flavor_extension(filename) is not None


def _get_vtk_flavor_extension(filename: str) -> Optional[str]:
    ext = splitext(filename)[1]
    return ext if ext in _VTK_EXTENSION_TO_READER else _sniff_vtk_flavor(filename)


def _sniff_vtk_flavor(filename: str, max_bytes_read: int = 1024) -> Optional[str]:
    with open(filename, "rb") as vtk_file:
        sniffed_content = vtk_file.read(max_bytes_read)
        split_content = sniffed_content.split(b"<VTKFile", maxsplit=1)
        if len(split_content) < 2:
            return None
        split_content = split_content[1].split(b"type=", maxsplit=1)
        if len(split_content) < 2:
            return None
        vtk_type = split_content[1].strip(b" ")
        if not vtk_type.startswith(b'"'):
            return None
        vtk_type = vtk_type[1:].split(b'"', maxsplit=1)[0]
        return _VTK_TYPE_TO_EXTENSION.get(vtk_type.decode())
