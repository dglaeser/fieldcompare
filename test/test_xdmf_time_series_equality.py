"""Test equality checks for fields obtained from xdfm time series files"""

from pathlib import Path

from context import fieldcompare
from fieldcompare import read_fields
from fieldcompare import FuzzyFieldEquality

TEST_DATA_PATH = Path(__file__).resolve().parent / Path("data")

def _compare_time_series_files(file1, file2, predicate=FuzzyFieldEquality()) -> bool:
    print("Start xdfm comparison")
    fields1 = read_fields(file1)
    fields2 = read_fields(file2)

    def _get_field2(name: str):
        for field in fields2:
            if field.name == name:
                return field
        raise ValueError("Field not found")

    for field1 in fields1:
        field2 = _get_field2(field1.name)
        print(f" -- comparing field {field1.name}")
        if not predicate(field1, field2):
            return False
    return True

def test_identical_time_series_files():
    assert _compare_time_series_files(
        TEST_DATA_PATH / Path("test_time_series.xdmf"),
        TEST_DATA_PATH / Path("test_time_series.xdmf")
    )

    assert _compare_time_series_files(
        TEST_DATA_PATH / Path("test_time_series_perturbed.xdmf"),
        TEST_DATA_PATH / Path("test_time_series_perturbed.xdmf")
    )

def test_perturbed_time_series_files():
    predicate = FuzzyFieldEquality()
    predicate.set_relative_tolerance(1e-5)
    predicate.set_absolute_tolerance(1e-5)
    assert _compare_time_series_files(
        TEST_DATA_PATH / Path("test_time_series.xdmf"),
        TEST_DATA_PATH / Path("test_time_series_perturbed.xdmf"),
        predicate
    )

    predicate.set_relative_tolerance(1e-20)
    predicate.set_absolute_tolerance(1e-20)
    assert not _compare_time_series_files(
        TEST_DATA_PATH / Path("test_time_series.xdmf"),
        TEST_DATA_PATH / Path("test_time_series_perturbed.xdmf"),
        predicate
    )

if __name__ == "__main__":
    test_identical_time_series_files()
    test_perturbed_time_series_files()
