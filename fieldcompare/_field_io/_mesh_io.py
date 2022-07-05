"""Reader for mesh file formats using meshio under the hood"""

from typing import Iterable, Dict, List, Tuple, Callable
from os.path import splitext
from xml.etree import ElementTree

from meshio import Mesh as _MeshIO_Mesh
from meshio import read as _meshio_read
from meshio import extension_to_filetypes as _meshio_supported_extensions
from meshio.xdmf import TimeSeriesReader as _MeshIOTimeSeriesReader

from .._logging import LoggableBase
from .._array import Array

from .._mesh_fields import (
    PointData,
    CellData,
    MeshFieldContainer,
    MeshFieldContainerInterface,
    TimeSeriesMeshFieldContainer
)
from .._mesh_fields import (
    remove_ghost_points as transform_remove_ghost_points,
    sort_point_coordinates as transform_sort_point_coordinates,
    sort_cells as transform_sort_cells,
    sort_cell_connectivity as transform_sort_cell_connectivity
)


class _Mesh:
    def __init__(self, points: Array, connectivity: Dict[str, Array]) -> None:
        self._points = points
        self._connectivity = connectivity

    @property
    def points(self) -> Array:
        return self._points

    @property
    def cell_types(self) -> Iterable[str]:
        return self._connectivity.keys()

    def connectivity(self, cell_type: str) -> Array:
        return self._connectivity[cell_type]


class MeshIOFieldReader(LoggableBase):
    def __init__(self,
                 permute_uniquely: bool = False,
                 remove_ghost_points: bool = False) -> None:
        super().__init__()
        self._do_permutation = permute_uniquely
        self._remove_ghost_points = remove_ghost_points

    @property
    def remove_ghost_points(self) -> bool:
        return self._remove_ghost_points

    @remove_ghost_points.setter
    def remove_ghost_points(self, value: bool) -> None:
        self._remove_ghost_points = value

    @property
    def permute_uniquely(self) -> bool:
        return self._do_permutation

    @permute_uniquely.setter
    def permute_uniquely(self, value: bool) -> None:
        self._do_permutation = value

    def read(self, filename: str) -> MeshFieldContainerInterface:
        if splitext(filename)[1] not in _meshio_supported_extensions:
            raise IOError("File type not supported by meshio")

        try:
            return self._read(filename)
        except Exception as e:
            raise IOError(f"Caught exception during reading of the mesh:\n{e}")

    def _read(self, filename: str) -> MeshFieldContainerInterface:
        if self._is_time_series(filename):
            return self._read_from_time_series(filename)
        return self._read_from_mesh(filename)

    def _is_time_series(self, filename: str) -> bool:
        return self._is_xdmf_time_series(filename)

    def _is_xdmf_time_series(self, filename: str) -> bool:
        extension = splitext(filename)[1]
        if extension not in [".xmf", ".xdmf"]:
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

    def _read_from_mesh(self, filename: str) -> MeshFieldContainerInterface:
        _meshio_mesh = _meshio_read(filename)
        mesh = _convert_meshio_mesh(_meshio_mesh)
        point_data = _extract_point_data(_meshio_mesh)
        cell_data = _extract_cell_data(_meshio_mesh)

        field_container: MeshFieldContainerInterface = MeshFieldContainer(mesh, point_data, cell_data)
        field_container = self._transform_mesh_fields(field_container)
        return field_container

    def _read_from_time_series(self, filename: str) -> MeshFieldContainerInterface:
        reader = _TimeSeriesReader(filename)
        mesh = reader.get_mesh()
        field_container: MeshFieldContainerInterface = TimeSeriesMeshFieldContainer(mesh, reader)
        field_container = self._transform_mesh_fields(field_container)
        return field_container

    def _transform_mesh_fields(self, mesh_fields: MeshFieldContainerInterface) -> MeshFieldContainerInterface:
        mesh_fields = self._transform_remove_ghost_points(mesh_fields)
        mesh_fields = self._transform_sort_mesh(mesh_fields)
        return mesh_fields

    def _transform_remove_ghost_points(self, mesh_fields: MeshFieldContainerInterface) -> MeshFieldContainerInterface:
        if self.remove_ghost_points:
            self._log("Removing ghost points\n", verbosity_level=1)
            return transform_remove_ghost_points(mesh_fields)
        return mesh_fields

    def _transform_sort_mesh(self, mesh_fields: MeshFieldContainerInterface) -> MeshFieldContainerInterface:
        if self.permute_uniquely:
            self._log("Sorting grid by coordinates to get a unique representation\n", verbosity_level=1)
            mesh_fields = transform_sort_point_coordinates(mesh_fields)
            mesh_fields = transform_sort_cell_connectivity(mesh_fields)
            mesh_fields = transform_sort_cells(mesh_fields)
        return mesh_fields


class _TimeSeriesReader:
    def __init__(self, filename: str) -> None:
        self._filename = filename
        self._meshio_reader = _MeshIOTimeSeriesReader(filename)
        self._meshio_mesh = _MeshIO_Mesh(*self._meshio_reader.read_points_cells())

    @property
    def num_time_steps(self) -> int:
        return self._meshio_reader.num_steps

    def point_data_names_of_time_step(self, time_step_index: int) -> List[str]:
        collection = self._meshio_reader.collection[time_step_index]
        return [str(attr.get("Name")) for attr in self._point_attributes(collection)]

    def cell_data_names_of_time_step(self, time_step_index: int) -> List[str]:
        collection = self._meshio_reader.collection[time_step_index]
        return [str(attr.get("Name")) for attr in self._cell_attributes(collection)]

    def read_time_step(self, time_step_index: int) -> Tuple[PointData, CellData]:
        _, point_data, cell_data = self._meshio_reader.read_data(time_step_index)
        _cell_data: CellData = {}
        for name in cell_data:
            _cell_data[name] = {
                cell_block.type: values
                for cell_block, values in zip(self._meshio_mesh.cells, cell_data[name])
            }
        return (point_data, _cell_data)

    def _point_attributes(self, collection) -> Iterable:
        return filter(lambda _e: _e.get("Center") == "Node", self._attributes(collection))

    def _cell_attributes(self, collection) -> Iterable:
        return filter(lambda _e: _e.get("Center") == "Cell", self._attributes(collection))

    def _attributes(self, collection) -> Iterable:
        return filter(lambda _e: _e.tag == "Attribute", collection)

    def get_mesh(self) -> _Mesh:
        return _convert_meshio_mesh(self._meshio_mesh)


def _register_readers_for_extensions(register_function: Callable[[str, MeshIOFieldReader], None]) -> None:
    for ext in _meshio_supported_extensions:
        register_function(ext, MeshIOFieldReader())


def _convert_meshio_mesh(mesh: _MeshIO_Mesh) -> _Mesh:
    return _Mesh(
        points=mesh.points,
        connectivity={
            cell_block.type: cell_block.data
            for cell_block in mesh.cells
        }
    )


def _extract_point_data(mesh: _MeshIO_Mesh) -> Dict[str, Array]:
    return mesh.point_data


def _extract_cell_data(mesh: _MeshIO_Mesh) -> Dict[str, Dict[str, Array]]:
    cell_data: dict = {}
    for name in mesh.cell_data:
        cell_data[name] = {}
        for cell_block, values in zip(mesh.cells, mesh.cell_data[name]):
            cell_data[name][cell_block.type] = values
    return cell_data
