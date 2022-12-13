from os import walk
from os.path import splitext
from pathlib import Path
from pytest import raises

from fieldcompare.mesh import read, read_sequence


def _get_vtk_file_name() -> str:
    test_data = Path(__file__).resolve().parent / Path("data")
    for _, _, files in walk(str(test_data)):
        for file in files:
            if splitext(file)[1] == ".vtu":
                return str(test_data / Path(file))
    raise FileNotFoundError("No vtk file found")


def _get_xdmf_time_series_file() -> str:
    test_data = Path(__file__).resolve().parent / Path("data")
    for _, _, files in walk(str(test_data)):
        for file in files:
            if splitext(file)[1] == ".xdmf" and "time" in file:
                return str(test_data / Path(file))
    raise FileNotFoundError("No xdmf time series file found")


def test_mesh_field_reading_vtk():
    _ = read(_get_vtk_file_name())


def test_mesh_field_sequence_reading():
    _ = read_sequence(_get_xdmf_time_series_file())


def test_mesh_field_reading_throws_io_error():
    with raises(IOError):
        _ = read("non_existing.csv")


def test_mesh_field_sequence_reading_with_mesh_file_throws_io_error():
    with raises(IOError):
        _ = read_sequence(_get_vtk_file_name())
