"""I/O mechanisms for fields defined on computational meshes"""
from os.path import splitext

from meshio import read as _meshio_read
from meshio import Mesh as MeshIOMesh
from meshio.xdmf import TimeSeriesReader as MeshIOTimeSeriesReader

from .._field_sequence import FieldDataSequence
from ._mesh_fields import MeshFields
from .meshio_utils import from_meshio


def read(filename: str) -> MeshFields:
    """Read the fields from the given mesh file"""
    return from_meshio(_meshio_read(filename))


def read_sequence(filename: str) -> FieldDataSequence:
    """Read a sequence from the given filename"""
    ext = splitext(filename)[1]
    if ext not in [".xmf", ".xdmf"]:
        raise NotImplementedError(f"Sequences from files with extension {ext}")
    return FieldDataSequence(source=_XDMFSequenceSource(filename))


class _XDMFSequenceSource:
    def __init__(self, filename: str) -> None:
        self._meshio_reader = MeshIOTimeSeriesReader(filename)
        self._mesh = from_meshio(
            MeshIOMesh(*self._meshio_reader.read_points_cells())
        ).domain
        self._step_idx = 0

    def reset(self) -> None:
        self._step_idx = 0

    def step(self) -> bool:
        self._step_idx += 1
        return self._step_idx < self._meshio_reader.num_steps

    def get(self) -> MeshFields:
        _, point_data, cell_data = self._meshio_reader.read_data(self._step_idx)
        return MeshFields(
            mesh=self._mesh,
            point_data=point_data,
            cell_data=cell_data
        )
