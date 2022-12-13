from os import walk
from os.path import splitext
from pathlib import Path
from pytest import raises

from fieldcompare.tabular import read


def _get_file_name_with_extension(ext: str) -> str:
    test_data = Path(__file__).resolve().parent / Path("data")
    for _, _, files in walk(str(test_data)):
        for file in files:
            if splitext(file)[1] == ext:
                return str(test_data / Path(file))
    raise FileNotFoundError(f"No file found with extension {ext}")


def _get_csv_file_name() -> str:
    return _get_file_name_with_extension(".csv")


def test_csv_field_reading_vtk():
    _ = read(_get_csv_file_name())


def test_csv_field_reading_with_vtk_throws_io_error():
    with raises(IOError):
        _ = read(_get_file_name_with_extension(".vtu"))
