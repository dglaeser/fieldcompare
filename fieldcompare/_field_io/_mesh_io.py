"""Reader for mesh file formats using meshio under the hood"""

from typing import Iterable, Tuple, Optional
from os.path import splitext

from meshio import Mesh
from meshio import read as meshio_read
from meshio import extension_to_filetypes as meshio_supported_extensions
from meshio.xdmf import TimeSeriesReader as MeshIOTimeSeriesReader

from ..field import DefaultFieldContainer
from ..logging import Logger, LoggableBase
from ..array import Array, sub_array
from ..array import make_initialized_array, make_uninitialized_array
from ..array import sort_array, accumulate
from ..mesh_fields import MeshFields, TimeSeriesMeshFields

from ._reader_map import _register_reader_for_extension


class MeshFieldReader(LoggableBase):
    class _LoggerAdapter:
        def __init__(self, reader) -> None:
            self._reader = reader

        def log(self, message: str, verbosity_level: int = 1) -> None:
            self._reader._log(message, verbosity_level)

        @property
        def verbosity_level(self) -> int:
            raise ValueError("Verbosity level cannot be accessed")

        @verbosity_level.setter
        def verbosity_level(self, value: int) -> None:
            raise ValueError("Verbosity level cannot be set")

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

    def read(self, filename: str) -> DefaultFieldContainer:
        assert splitext(filename)[1] in meshio_supported_extensions

        try:
            return self._read(filename)
        except Exception as e:
            raise IOError(f"Caught exception during reading of the mesh:\n{e}")

    def _read(self, filename: str) -> DefaultFieldContainer:
        extension = splitext(filename)[1]
        if _is_time_series_compatible_format(extension):
            return DefaultFieldContainer(
                _extract_from_meshio_time_series(
                    MeshIOTimeSeriesReader(filename),
                    self.remove_ghost_points,
                    self.permute_uniquely,
                    self._LoggerAdapter(self)
                )
            )
        return DefaultFieldContainer(
            _extract_from_meshio_mesh(
                meshio_read(filename),
                self.remove_ghost_points,
                self.permute_uniquely,
                self._LoggerAdapter(self)
            )
        )

for ext in meshio_supported_extensions:
    _register_reader_for_extension(ext, MeshFieldReader())


def _is_time_series_compatible_format(file_ext: str) -> bool:
    return file_ext in [".xmf", ".xdmf"]


def _filter_out_ghost_points(mesh: Mesh, logger: Logger) -> Tuple[Mesh, Array]:
    logger.log("Removing ghost points\n", verbosity_level=1)
    is_ghost = make_initialized_array(size=len(mesh.points), dtype=bool, init_value=True)
    for _, corners in _cells(mesh):
        for p_idx in corners.flatten():
            is_ghost[p_idx] = False

    num_ghosts = accumulate(is_ghost)
    first_ghost_index_after_sort = int(len(is_ghost) - num_ghosts)

    ghost_filter_map = sort_array(is_ghost)
    ghost_filter_map = sub_array(ghost_filter_map, 0, first_ghost_index_after_sort)
    ghost_filter_map_inverse = make_uninitialized_array(size=len(mesh.points), dtype=int)
    for new_index, old_index in enumerate(ghost_filter_map):
        ghost_filter_map_inverse[old_index] = new_index

    def _map_corners(corners_array):
        for idx, corners in enumerate(corners_array):
            corners_array[idx] = ghost_filter_map_inverse[corners_array[idx]]
        return corners_array

    return Mesh(
        points=mesh.points[ghost_filter_map],
        cells=[(cell_type, _map_corners(corners)) for cell_type, corners in _cells(mesh)],
        point_data={name: mesh.point_data[name][ghost_filter_map] for name in mesh.point_data},
        cell_data=mesh.cell_data
    ), ghost_filter_map


def _extract_from_meshio_mesh(mesh: Mesh,
                              remove_ghost_points: bool,
                              permute_uniquely: bool,
                              logger: Logger) -> MeshFields:
    logger.log("Extracting fields from mesh file\n", verbosity_level=1)
    if remove_ghost_points:
        mesh, _ = _filter_out_ghost_points(mesh, logger)
    result = MeshFields(
        (mesh.points, _cells(mesh)),
        permute_uniquely,
    )
    result.attach_logger(logger)

    for array_name in mesh.point_data:
        result.add_point_data(array_name, mesh.point_data[array_name])
    for array_name in mesh.cell_data:
        result.add_cell_data(
            array_name,
            (
                (cell_type, values)
                for (cell_type, _), values in zip(_cells(mesh), mesh.cell_data[array_name])
            )
        )
    return result


def _extract_from_meshio_time_series(time_series_reader,
                                     remove_ghost_points: bool,
                                     permute_uniquely: bool,
                                     logger: Logger) -> TimeSeriesMeshFields:
    logger.log("Extracting points/cells from time series file\n", verbosity_level=1)
    points, cells = time_series_reader.read_points_cells()
    mesh = Mesh(points, cells)
    ghost_point_filter = None
    if remove_ghost_points:
        mesh, ghost_point_filter = _filter_out_ghost_points(mesh, logger)
    time_steps_reader = _MeshioTimeStepReader(mesh, time_series_reader, ghost_point_filter)
    result = TimeSeriesMeshFields(
        (mesh.points, _cells(mesh)),
        time_steps_reader,
        permute_uniquely
    )
    result.attach_logger(logger)
    return result


class _MeshioTimeStepReader:
    def __init__(self,
                 mesh: Mesh,
                 meshio_reader: MeshIOTimeSeriesReader,
                 ghost_point_filter: Optional[Array] = None) -> None:
        self._mesh = mesh
        self._reader = meshio_reader
        self._num_time_steps = meshio_reader.num_steps
        self._ghost_point_filter = ghost_point_filter

    @property
    def num_time_steps(self) -> int:
        """Return the number of time steps that can be read"""
        return self._num_time_steps

    def read_time_step(self, time_step_index: int) -> Tuple:
        """Read the time step with the given index"""
        _, point_data, cell_data = self._reader.read_data(time_step_index)
        point_data = [
            (name, self._transform_point_data(point_data[name]))
            for name in point_data
        ]
        cell_data = [
            (
                name,
                [
                    (cell_type, values)
                    for (cell_type, _), values in zip(_cells(self._mesh), cell_data[name])
                ]
            )
            for name in cell_data
        ]
        return point_data, cell_data

    def _transform_point_data(self, point_data: Array) -> Array:
        if self._ghost_point_filter is not None:
            return point_data[self._ghost_point_filter]
        return point_data


def _cells(mesh: Mesh) -> Iterable[Tuple[str, Array]]:
    return ((cell_block.type, cell_block.data) for cell_block in mesh.cells)
