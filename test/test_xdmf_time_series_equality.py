"""Test equality checks for fields obtained from xdfm time series files"""

import pytest
from pathlib import Path

from fieldcompare.mesh import sort, protocols as mesh_protocols
from fieldcompare.io import _mesh_io
from fieldcompare.predicates import FuzzyEquality, DefaultEquality
from fieldcompare import FieldDataComparator, protocols

if not _mesh_io._HAVE_MESHIO:
    pytest.skip(
        "Skipping xdmf time series tests because meshio was not found",
        allow_module_level=True
    )

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
    sequence1 = _mesh_io._read(file1)
    sequence2 = _mesh_io._read(file2)
    assert isinstance(sequence1, protocols.FieldDataSequence)
    assert isinstance(sequence2, protocols.FieldDataSequence)

    for fields1, fields2 in zip(sequence1, sequence2):
        assert isinstance(fields1, mesh_protocols.MeshFields)
        assert isinstance(fields2, mesh_protocols.MeshFields)
        fields1.domain.set_tolerances(abs_tol=predicate.absolute_tolerance, rel_tol=predicate.relative_tolerance)
        fields2.domain.set_tolerances(abs_tol=predicate.absolute_tolerance, rel_tol=predicate.relative_tolerance)
        fields1 = sort(fields1)
        fields2 = sort(fields2)
        if not FieldDataComparator(fields1, fields2)(
            predicate_selector=lambda _, __: predicate
        ):
            return CheckResult(False)
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


def test_permutated_time_series_files():
    assert _compare_time_series_files(
        TEST_DATA_PATH / Path("test_time_series.xdmf"),
        TEST_DATA_PATH / Path("test_time_series_permutated.xdmf")
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

    default_predicate.relative_tolerance = 1e-20
    default_predicate.absolute_tolerance = 1e-20
    test_result = _compare_time_series_files(
        TEST_DATA_PATH / Path("test_time_series.xdmf"),
        TEST_DATA_PATH / Path("test_time_series_perturbed.xdmf"),
        default_predicate
    )
    assert not test_result
