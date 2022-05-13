from os import remove
from pathlib import Path

from _common import make_test_mesh, PointDataStorage, CellDataStorage
from _common import make_point_data_array, make_cell_data_arrays
from _common import write_time_series

from fieldcompare import read_fields, make_field_reader, make_mesh_field_reader
from fieldcompare import is_mesh_file, is_supported_file

_TEST_DATA_PATH = Path(__file__).parent / Path("data")


def test_is_supported_file():
    assert is_supported_file("test.vtk")
    assert is_supported_file("test.vtu")
    assert is_supported_file("test.xdmf")
    assert is_supported_file("test.xmf")


def test_is_mesh_file():
    assert is_mesh_file("test.vtk")
    assert is_mesh_file("test.vtu")
    assert is_mesh_file("test.xdmf")
    assert is_mesh_file("test.xmf")
    assert not is_mesh_file("test.csv")


def test_field_reader_creation():
    file_path = _TEST_DATA_PATH / Path("test_mesh.vtu")
    reader = make_field_reader(str(file_path))
    for field in reader.read(str(file_path)):
        assert field.name


def test_mesh_field_reader_creation():
    file_path = _TEST_DATA_PATH / Path("test_mesh.vtu")
    reader = make_mesh_field_reader(str(file_path))
    for field in reader.read(str(file_path)):
        assert field.name


def test_time_series_field_names():
    mesh = make_test_mesh()
    ts_point_data = [PointDataStorage()]*2
    ts_cell_data = [CellDataStorage()]*2
    ts_point_data[0].add("pfield", make_point_data_array(mesh))
    ts_point_data[1].add("pfield", make_point_data_array(mesh))
    ts_cell_data[0].add("cfield", make_cell_data_arrays(mesh))
    ts_cell_data[1].add("cfield", make_cell_data_arrays(mesh))

    test_filename = "test_time_series_fields"
    test_filename_xdmf = f"{test_filename}.xdmf"
    test_filename_h5 = f"{test_filename}.h5"

    write_time_series(test_filename_xdmf, mesh, ts_point_data, ts_cell_data)
    fields = read_fields(test_filename_xdmf)
    assert "pfield_timestep_0" in fields.field_names
    assert "pfield_timestep_1" in fields.field_names
    assert "cfield_triangle_timestep_0" in fields.field_names
    assert "cfield_triangle_timestep_1" in fields.field_names
    assert "cfield_quad_timestep_0" in fields.field_names
    assert "cfield_quad_timestep_1" in fields.field_names
    remove(test_filename_xdmf)
    remove(test_filename_h5)
