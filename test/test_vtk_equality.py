"""Test equality of fields read from vtk files"""

from pathlib import Path

from context import fieldcompare
from fieldcompare import predicates, read_fields
from fieldcompare import FuzzyFieldEquality
from fieldcompare.predicates import PredicateResult

TEST_DATA_PATH = Path(__file__).resolve().parent / Path("data")

def _get_field_from_list(name, fields_list):
    element_list = list(filter(lambda f: f.name == name, fields_list))
    assert len(element_list) == 1
    return element_list[0]

def _compare_vtk_files(file1, file2, predicate=FuzzyFieldEquality) -> PredicateResult:
    fields1 = read_fields(file1)
    fields2 = read_fields(file2)
    for field1 in fields1:
        field2 = _get_field_from_list(field1.name, fields2)
        pred_result = predicate(field1, field2)
        if not pred_result:
            return pred_result
    return PredicateResult(True)


def test_identical_vtk_files():
    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh.vtu"),
        TEST_DATA_PATH / Path("test_mesh.vtu")
    )

    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh_permutated.vtu"),
        TEST_DATA_PATH / Path("test_mesh_permutated.vtu")
    )

def test_vtk_files_permutated():
    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh.vtu"),
        TEST_DATA_PATH / Path("test_mesh_permutated.vtu")
    )

def test_vtk_files_perturbed():
    predicate = FuzzyFieldEquality()
    predicate.set_relative_tolerance(1e-5)
    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh.vtu"),
        TEST_DATA_PATH / Path("test_mesh_permutated_perturbed.vtu"),
        predicate
    )

    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh_permutated.vtu"),
        TEST_DATA_PATH / Path("test_mesh_permutated_perturbed.vtu"),
        predicate
    )

    predicate.set_relative_tolerance(1e-20)
    predicate.set_absolute_tolerance(0.0)
    assert not _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh.vtu"),
        TEST_DATA_PATH / Path("test_mesh_permutated_perturbed.vtu"),
        predicate
    )

    assert not _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh_permutated.vtu"),
        TEST_DATA_PATH / Path("test_mesh_permutated_perturbed.vtu"),
        predicate
    )

if __name__ == "__main__":
    test_identical_vtk_files()
    test_vtk_files_permutated()
    test_vtk_files_perturbed()
