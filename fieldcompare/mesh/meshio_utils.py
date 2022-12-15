"""Utility functions for interoperability with meshio"""

from os.path import splitext
from typing import Dict, List
from numpy.typing import ArrayLike
from xml.etree import ElementTree

try:
    from meshio import read as _meshio_read
    from meshio import extension_to_filetypes as _MESHIO_SUPPORTED_EXTENSIONS
    from meshio import Mesh as MeshIOMesh
    from meshio.xdmf import TimeSeriesReader as MeshIOTimeSeriesReader
    from meshio._vtk_common import vtk_to_meshio_type, meshio_to_vtk_type  # type: ignore[import]
    _HAVE_MESH_IO = True
except ImportError:
    from typing import Any
    _HAVE_MESH_IO = False
    MeshIOMesh = Any

from .._field_sequence import FieldDataSequence
from ._vtk._helpers import _VTK_CELL_TYPE_STR_TO_INDEX, _VTK_CELL_TYPE_TO_STR
from ._mesh_fields import MeshFields, remove_cell_type_suffix
from ._mesh import Mesh
from .protocols import MeshFields as MeshFieldsInterface


def from_meshio(mesh: MeshIOMesh) -> MeshFields:
    """Convert a mesh data structure of the meshio library into MeshFields"""
    return MeshFields(
        mesh=Mesh(
            mesh.points,
            ((_from_meshio_cell_type(block.type), block.data) for block in mesh.cells)
        ),
        point_data=mesh.point_data,
        cell_data=mesh.cell_data
    )


def to_meshio(mesh_fields: MeshFieldsInterface) -> MeshIOMesh:
    """Convert MeshFields into a mesh of the meshio library"""
    if not _HAVE_MESH_IO:
        raise ModuleNotFoundError("MeshIO required for conversion to meshio-mesh")

    types = [ct for ct in mesh_fields.domain.cell_types]
    cell_data: Dict[str, List[ArrayLike]] = {}
    for field, cell_type in mesh_fields.cell_fields_types:
        name = remove_cell_type_suffix(cell_type, field.name)
        if name not in cell_data:
            cell_data[name] = [[] for _ in range(len(types))]
        cell_data[name][types.index(cell_type)] = [v for v in field.values]

    return MeshIOMesh(
        points=mesh_fields.domain.points,
        cells={_to_meshio_cell_type(ct): mesh_fields.domain.connectivity(ct) for ct in types},
        point_data={field.name: field.values for field in mesh_fields.point_fields},
        cell_data={name: data for name, data in cell_data.items()}
    )


def _is_supported(filename: str) -> bool:
    if not _HAVE_MESH_IO:
        return False
    return splitext(filename)[1] in _MESHIO_SUPPORTED_EXTENSIONS


def _is_supported_sequence(filename: str) -> bool:
    if not _HAVE_MESH_IO:
        return False
    if splitext(filename)[1] not in [".xmf", ".xdmf"]:
        return False

    parser = ElementTree.XMLParser()
    tree = ElementTree.parse(filename, parser)
    root = tree.getroot()
    if root.tag != "Xdmf":
        return False
    for domain in filter(lambda d: d.tag == "Domain", root):
        for grid in filter(lambda g: g.tag == "Grid", domain):
            if grid.get("GridType") == "Collection" \
                    and grid.get("CollectionType") == "Temporal":
                return True
    return False


def _read(filename: str) -> MeshFields:
    if not _HAVE_MESH_IO:
        raise IOError("MeshIO module not found")
    try:
        return from_meshio(_meshio_read(filename))
    except Exception as e:
        raise IOError(f"Error reading with meshio-io: '{e}'")


def _read_sequence(filename: str) -> FieldDataSequence:
    if not _HAVE_MESH_IO:
        raise IOError("MeshIO module not found")

    try:
        return FieldDataSequence(source=_XDMFSequenceSource(filename))
    except Exception as e:
        raise IOError(f"Error reading mesh sequence with meshio: '{e}'")


def _from_meshio_cell_type(cell_type: str) -> str:
    return _VTK_CELL_TYPE_TO_STR[meshio_to_vtk_type[cell_type]]


def _to_meshio_cell_type(cell_type: str) -> str:
    if cell_type in meshio_to_vtk_type:
        return cell_type
    return vtk_to_meshio_type[_VTK_CELL_TYPE_STR_TO_INDEX[cell_type]]


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

    @property
    def number_of_steps(self) -> int:
        return self._meshio_reader.num_steps
