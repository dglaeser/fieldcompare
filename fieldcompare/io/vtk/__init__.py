# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""I/O facilities for reading field data from VTK files"""

from __future__ import annotations
from os.path import splitext

from .. import protocols

from ._vtp_reader import VTPReader
from ._vts_reader import VTSReader
from ._vtr_reader import VTRReader
from ._vti_reader import VTIReader
from ._vtu_reader import VTUReader
from ._pvtk_readers import PVTPReader, PVTUReader, PVTSReader, PVTRReader, PVTIReader
from ._pvd_reader import PVDReader

from ._reader_map import _VTK_EXTENSION_TO_READER, _VTK_TYPE_TO_EXTENSION

from ._vtu_writer import VTUWriter


def read(filename: str) -> protocols.FieldData | protocols.FieldDataSequence:
    """Read field data from the given VTK file"""
    ext = _get_vtk_flavor_extension(filename)
    if ext is None:
        raise IOError(f"Could not determine VTK flavor of '{filename}'")
    return _VTK_EXTENSION_TO_READER[ext](filename).read()


def is_supported(filename: str) -> bool:
    """Return true if the given file can be read by the VTK readers"""
    return _get_vtk_flavor_extension(filename) is not None


def _get_vtk_flavor_extension(filename: str) -> str | None:
    ext = splitext(filename)[1]
    return ext if ext in _VTK_EXTENSION_TO_READER else _sniff_vtk_flavor(filename)


def _sniff_vtk_flavor(filename: str, max_bytes_read: int = 1024) -> str | None:
    with open(filename, "rb") as vtk_file:
        sniffed_content = vtk_file.read(max_bytes_read)
        split_content = sniffed_content.split(b"<VTKFile", maxsplit=1)
        if len(split_content) < 2:  # noqa: PLR2004
            return None
        split_content = split_content[1].split(b"type=", maxsplit=1)
        if len(split_content) < 2:  # noqa: PLR2004
            return None
        vtk_type = split_content[1].strip(b" ")
        if not vtk_type.startswith(b'"'):
            return None
        vtk_type = vtk_type[1:].split(b'"', maxsplit=1)[0]
        return _VTK_TYPE_TO_EXTENSION.get(vtk_type.decode())


__all__ = [
    "PVDReader",
    "PVTPReader",
    "PVTUReader",
    "PVTSReader",
    "PVTRReader",
    "PVTIReader",
    "VTPReader",
    "VTUReader",
    "VTSReader",
    "VTRReader",
    "VTIReader",
    "VTUWriter",
    "read",
    "is_supported",
]
