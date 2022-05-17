"""Test equality checks for fields obtained from xdfm time series files"""

from pathlib import Path

from fieldcompare import read_fields, FuzzyEquality, DefaultEquality


TEST_DATA_PATH = Path(__file__).resolve().parent / Path("data")


class CheckResult:
    def __init__(self, value: bool, msg: str = "") -> None:
        self._value = value
        self._msg = msg

    def __bool__(self) -> bool:
        return self._value

    @property
    def report(self) -> str:
        return self._msg


def _compare_time_series_files(file1, file2, predicate=FuzzyEquality()) -> CheckResult:
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
        check = predicate(field1.values, field2.values)
        if not check:
            return CheckResult(False, f"Field {field1.name} has compared unequal")
    return CheckResult(True)


def test_identical_time_series_files():
    assert _compare_time_series_files(
        TEST_DATA_PATH / Path("test_time_series.xdmf"),
        TEST_DATA_PATH / Path("test_time_series.xdmf")
    )
    assert _compare_time_series_files(
        TEST_DATA_PATH / Path("test_time_series.xdmf"),
        TEST_DATA_PATH / Path("test_time_series.xdmf"),
        DefaultEquality()
    )

    assert _compare_time_series_files(
        TEST_DATA_PATH / Path("test_time_series_perturbed.xdmf"),
        TEST_DATA_PATH / Path("test_time_series_perturbed.xdmf")
    )
    assert _compare_time_series_files(
        TEST_DATA_PATH / Path("test_time_series_perturbed.xdmf"),
        TEST_DATA_PATH / Path("test_time_series_perturbed.xdmf"),
        DefaultEquality()
    )


def test_perturbed_time_series_files():
    predicate = FuzzyEquality()
    default_predicate = DefaultEquality()
    predicate.relative_tolerance = 1e-5
    predicate.absolute_tolerance = 1e-5
    default_predicate.relative_tolerance = 1e-5
    default_predicate.absolute_tolerance = 1e-5

    assert _compare_time_series_files(
        TEST_DATA_PATH / Path("test_time_series.xdmf"),
        TEST_DATA_PATH / Path("test_time_series_perturbed.xdmf"),
        predicate
    )
    assert _compare_time_series_files(
        TEST_DATA_PATH / Path("test_time_series.xdmf"),
        TEST_DATA_PATH / Path("test_time_series_perturbed.xdmf"),
        default_predicate
    )

    predicate.relative_tolerance = 1e-20
    predicate.absolute_tolerance = 1e-20
    test_result = _compare_time_series_files(
        TEST_DATA_PATH / Path("test_time_series.xdmf"),
        TEST_DATA_PATH / Path("test_time_series_perturbed.xdmf"),
        predicate
    )
    assert not test_result
    assert "timestep_2" in test_result.report

    default_predicate.relative_tolerance = 1e-20
    default_predicate.absolute_tolerance = 1e-20
    test_result = _compare_time_series_files(
        TEST_DATA_PATH / Path("test_time_series.xdmf"),
        TEST_DATA_PATH / Path("test_time_series_perturbed.xdmf"),
        default_predicate
    )
    assert not test_result
    assert "timestep_2" in test_result.report
