"""Reader for mesh file formats using meshio under the hood"""

from typing import Iterator, List, Tuple, Callable
from os.path import splitext
from dataclasses import dataclass
from xml.etree import ElementTree

from meshio import Mesh as _MeshIO_Mesh
from meshio import read as _meshio_read
from meshio import extension_to_filetypes as _meshio_supported_extensions
from meshio.xdmf import TimeSeriesReader as _MeshIOTimeSeriesReader

from ..field import Field, FieldContainer, DefaultFieldContainer
from ..logging import LoggableBase
from ..array import Array

from ._mesh import Mesh, DefaultMesh, TransformedMesh, TransformedMeshBase
from ._mesh import transform_identity, transform_without_ghosts, transform_sorted


class _TimeSeriesFieldContainer:
    """
        A field container that contains the fields of multiple time steps.
        To save memory, it never stores more than the fields of one time step.
        If the fields of the next time step are requested, they are read in lazily.
    """
    @dataclass
    class _FieldInfo:
        name: str
        data_type: str

    @dataclass
    class _TimestepData:
        point_data: dict
        cell_data: dict
        step_idx: int

    def __init__(self,
                 time_series_reader: _MeshIOTimeSeriesReader,
                 meshio_mesh: _MeshIO_Mesh,
                 transformed_mesh: TransformedMesh) -> None:
        self._time_series_reader = time_series_reader
        self._meshio_mesh = meshio_mesh
        self._transformed_mesh = transformed_mesh
        self._field_infos = self._find_fields_of_all_timesteps()
        self._timestep_data = self._TimestepData({}, {}, -1)

    @property
    def field_names(self) -> List[str]:
        return [_f.name for _f in self._field_infos]

    def get(self, field_name: str) -> Field:
        for _info in self._field_infos:
            if _info.name == field_name:
                step_idx = int(field_name.split("timestep_")[1])
                self._prepare_step_data(step_idx)
                return self._get_field(field_name, _info.data_type)
        raise ValueError(f"Could not find field {field_name}")

    def __iter__(self) -> Iterator[Field]:
        return iter((self.get(field_name) for field_name in self.field_names))

    def _prepare_step_data(self, step_idx: int) -> None:
        if step_idx != self._timestep_data.step_idx:
            _, point_data, cell_data = self._time_series_reader.read_data(step_idx)
            self._timestep_data = self._TimestepData(point_data, cell_data, step_idx)

    def _get_field(self, name: str, data_type: str) -> Field:
        if data_type == "point_data":
            return self._get_point_data_field(name)
        elif data_type == "cell_data":
            return self._get_cell_data_field(name)
        raise ValueError("Unknown data type")

    def _get_point_data_field(self, name: str) -> Field:
        base_name = name.split("_timestep_")[0]
        return Field(name, self._timestep_data.point_data[base_name])

    def _get_cell_data_field(self, name: str) -> Field:
        base_name_with_cell_type = name.split("_timestep_")[0]
        base_name, cell_type = self._split_cell_type_suffix(base_name_with_cell_type)
        for cell_block, cell_data in zip(self._meshio_mesh.cells,
                                         self._timestep_data.cell_data[base_name]):
            if cell_block.type == cell_type:
                return Field(name, cell_data)
        raise ValueError(f"Could not get the field with name {name}")

    def _split_cell_type_suffix(self, name: str) -> Tuple[str, str]:
        for cell_type in self._transformed_mesh.connectivity:
            if name.endswith(cell_type):
                return name.rsplit(f"_{cell_type}")[0], cell_type
        raise ValueError("Did not find a cell type suffix on the given name")

    def _find_fields_of_all_timesteps(self) -> List[_FieldInfo]:
        fields = []
        for step in range(self._time_series_reader.num_steps):
            fields.extend(self._find_fields_of_step(step))
        return fields

    def _find_fields_of_step(self, step_idx: int) -> List[_FieldInfo]:
        fields = []
        for element in list(self._time_series_reader.collection[step_idx]):
            if element.tag == "Attribute":
                fields.extend(self._get_element_field_infos(step_idx, element))
        return fields

    def _get_element_field_infos(self, step_idx: int, xdmf_element) -> List[_FieldInfo]:
        if xdmf_element.get("Center") == "Node":
            return [self._FieldInfo(
                self._make_step_field_name(step_idx, xdmf_element.get("Name")),
                "point_data"
            )]
        elif xdmf_element.get("Center") == "Cell":
            name = xdmf_element.get("Name")
            return [
                self._FieldInfo(
                    self._make_step_field_name(step_idx, f"{name}_{cell_type}"),
                    "cell_data"
                )
                for cell_type in self._transformed_mesh.connectivity
            ]

        raise IOError("Can only read point or cell data")

    def _make_step_field_name(self, step_idx: int, name: str) -> str:
        return f"{name}_timestep_{step_idx}"


class MeshIOFieldReader(LoggableBase):
    def __init__(self,
                 permute_uniquely: bool = True,
                 remove_ghost_points: bool = True) -> None:
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

    def read(self, filename: str) -> FieldContainer:
        if splitext(filename)[1] not in _meshio_supported_extensions:
            raise IOError("File type not supported by meshio")

        try:
            return self._read(filename)
        except Exception as e:
            raise IOError(f"Caught exception during reading of the mesh:\n{e}")

    def _read(self, filename: str) -> FieldContainer:
        self._log(f"Reading fields from '{filename}'", verbosity_level=1)
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

    def _read_from_mesh(self, filename: str) -> DefaultFieldContainer:
        _meshio_mesh = _meshio_read(filename)
        mesh = _convert_meshio_mesh(_meshio_mesh)
        transformed_mesh = self._transform(mesh)

        fields = []
        fields.append(Field("point_coordinates", transformed_mesh.points))
        for cell_type, corners in mesh.connectivity.items():
            fields.append(Field(f"{cell_type}_corners", corners))
        for name in _meshio_mesh.point_data:
            fields.append(Field(
                f"{name}",
                transformed_mesh.transform_point_data(
                    _meshio_mesh.point_data[name]
                )
            ))
        for name in _meshio_mesh.cell_data:
            for cell_block, values in zip(_meshio_mesh.cells, _meshio_mesh.cell_data[name]):
                fields.append(Field(
                    f"{name}_{cell_block.type}",
                    transformed_mesh.transform_cell_data(cell_block.type, values)
                ))
        return DefaultFieldContainer(fields)

    def _read_from_time_series(self, filename: str) -> _TimeSeriesFieldContainer:
        _meshio_reader = _MeshIOTimeSeriesReader(filename)
        _meshio_mesh = _MeshIO_Mesh(*_meshio_reader.read_points_cells())
        transformed_mesh = self._transform(_convert_meshio_mesh(_meshio_mesh))
        return _TimeSeriesFieldContainer(_meshio_reader, _meshio_mesh, transformed_mesh)

    def _transform(self, mesh: Mesh) -> TransformedMesh:
        class ComposedTransformedMesh(TransformedMeshBase):
            def __init__(self,
                         mesh: Mesh,
                         first_trafo_factory: Callable[[Mesh], TransformedMesh],
                         second_trafo_factory: Callable[[Mesh], TransformedMesh]) -> None:
                self._first_trafo = first_trafo_factory(mesh)
                self._second_trafo = second_trafo_factory(self._first_trafo.mesh())
                super().__init__(self._second_trafo.points, self._second_trafo.connectivity)

            def transform_point_data(self, data: Array) -> Array:
                return self._second_trafo.transform_point_data(
                    self._first_trafo.transform_point_data(data)
                )

            def transform_cell_data(self, cell_type: str, data: Array) -> Array:
                return self._second_trafo.transform_cell_data(
                    cell_type,
                    self._first_trafo.transform_cell_data(cell_type, data)
                )
        return ComposedTransformedMesh(
            mesh,
            self._transform_without_ghosts,
            self._transform_sorted
        )

    def _transform_without_ghosts(self, mesh: Mesh) -> TransformedMesh:
        if self.remove_ghost_points:
            self._log("Removing ghost points", verbosity_level=2)
            return transform_without_ghosts(mesh)
        return transform_identity(mesh)

    def _transform_sorted(self, mesh: Mesh) -> TransformedMesh:
        if self.permute_uniquely:
            self._log("Sorting grid by coordinates to get a unique representation")
            return transform_sorted(mesh)
        return transform_identity(mesh)


def _register_readers_for_extensions(register_function: Callable[[str, MeshIOFieldReader], None]) -> None:
    for ext in _meshio_supported_extensions:
        register_function(ext, MeshIOFieldReader())


def _convert_meshio_mesh(mesh: _MeshIO_Mesh) -> Mesh:
    return DefaultMesh(
        points=mesh.points,
        connectivity={
            cell_block.type: cell_block.data for cell_block in mesh.cells
        }
    )
