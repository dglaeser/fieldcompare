# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Read fields from mesh files with meshio"""

from __future__ import annotations
from os.path import splitext
from xml.etree import ElementTree

try:
    from meshio import extension_to_filetypes as _meshio_extension_to_filetypes
    from meshio import read as _meshio_read, Mesh as _MeshIOMesh
    from meshio.xdmf import TimeSeriesReader as _MeshioTimeSeriesReader
    from ..mesh import meshio_utils

    _MESHIO_SUPPORTED_EXTENSIONS = _meshio_extension_to_filetypes
    _HAVE_MESHIO = True
except ImportError:
    _HAVE_MESHIO = False

from .. import protocols, FieldDataSequence
from ..mesh import MeshFields


def _read(filename: str) -> protocols.FieldData | protocols.FieldDataSequence:
    if _is_xdmf_sequence(filename):
        return FieldDataSequence(source=_XDMFSequenceSource(filename))
    return meshio_utils.from_meshio(_meshio_read(filename))


def _is_supported(filename: str) -> bool:
    return splitext(filename)[1] in _MESHIO_SUPPORTED_EXTENSIONS


def _is_xdmf_sequence(filename: str) -> bool:
    if splitext(filename)[1] not in [".xmf", ".xdmf"]:
        return False

    root = ElementTree.parse(filename).getroot()
    if root.tag != "Xdmf":
        return False
    for domain in filter(lambda d: d.tag == "Domain", root):
        for grid in filter(lambda g: g.tag == "Grid", domain):
            if grid.get("GridType") == "Collection" and grid.get("CollectionType") == "Temporal":
                return True
    return False


class _XDMFSequenceSource:
    def __init__(self, filename: str) -> None:
        self._meshio_reader = _MeshioTimeSeriesReader(filename)
        self._mesh = meshio_utils.from_meshio(_MeshIOMesh(*self._meshio_reader.read_points_cells())).domain
        self._step_idx = 0

    def reset(self) -> None:
        self._step_idx = 0

    def step(self) -> bool:
        self._step_idx += 1
        return self._step_idx < self._meshio_reader.num_steps

    def get(self) -> MeshFields:
        _, point_data, cell_data = self._meshio_reader.read_data(self._step_idx)
        return MeshFields(mesh=self._mesh, point_data=point_data, cell_data=cell_data)

    @property
    def number_of_steps(self) -> int:
        return self._meshio_reader.num_steps
