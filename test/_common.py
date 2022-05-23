from typing import Dict, List

from meshio import Mesh as MeshIOMesh
from meshio.xdmf import TimeSeriesWriter as MeshIOTimeSeriesWriter

from fieldcompare import Array, make_array
from fieldcompare._field_io._mesh_io import _Mesh as Mesh


class PointDataStorage:
    def __init__(self):
        self._fields: Dict[str, Array] = {}

    def add(self, name: str, data: Array) -> None:
        self._fields[name] = data

    def as_dict(self) -> Dict[str, Array]:
        return self._fields


class CellDataStorage:
    def __init__(self):
        self._fields: Dict[str, Dict[str, Array]] = {}

    def add(self, name: str, data: Dict[str, Array]) -> None:
        self._fields[name] = data

    def as_dict(self) -> Dict[str, Dict[str, Array]]:
        return self._fields


def _test_function(x: float, y: float) -> float:
    return (1.0 - x)*(1.0 - y)


def make_test_mesh() -> Mesh:
    points = make_array([
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [1.0, 1.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.5, 0.5, 0.0],
        [2.0, 0.0, 0.0],
        [2.0, 1.0, 0.0]
    ])

    cells = {
        "triangle": make_array([
            [0, 1, 4],
            [1, 2, 4],
            [2, 3, 4],
            [3, 0, 4]
        ]),
        "quad": make_array([[1, 5, 6, 2]])
    }

    return Mesh(points, cells)


def make_point_data_array(mesh: Mesh) -> Array:
    return make_array([_test_function(p[0], p[1]) for p in mesh.points])


def make_cell_data_arrays(mesh: Mesh) -> Dict[str, Array]:
    return {
        cell_type: make_array([
            float(i) for i in range(len(mesh.connectivity(cell_type)))
        ])
        for cell_type in mesh.cell_types
    }


def write_file(filename,
               mesh: Mesh,
               point_data: PointDataStorage,
               cell_data: CellDataStorage) -> None:
    meshio_mesh = MeshIOMesh(
        points=mesh.points,
        cells=[
            (cell_type, mesh.connectivity(cell_type))
            for cell_type in mesh.cell_types
        ],
        point_data=point_data.as_dict(),
        cell_data=_convert_to_meshio_cell_data(cell_data.as_dict())
    )
    meshio_mesh.write(filename)


def write_time_series(filename,
                      mesh: Mesh,
                      point_data: List[PointDataStorage],
                      cell_data: List[CellDataStorage]) -> None:
    assert len(point_data) == len(cell_data)
    num_time_steps = len(point_data)

    with MeshIOTimeSeriesWriter(filename) as writer:
        writer.write_points_cells(
            mesh.points,
            {ct: mesh.connectivity(ct) for ct in mesh.cell_types}
        )
        for ts in range(num_time_steps):
            writer.write_data(
                ts, point_data[ts].as_dict(), _convert_to_meshio_cell_data(cell_data[ts].as_dict())
            )


def _convert_to_meshio_cell_data(cell_data_dict):
    return {
        name: [values for _, values in cell_data_dict[name].items()]
        for name in cell_data_dict
    }
