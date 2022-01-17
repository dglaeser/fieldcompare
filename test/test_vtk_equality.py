"""Test equality of fields read from vtk files"""

from pathlib import Path

from context import fieldcompare
from fieldcompare import predicates, read_fields
from fieldcompare import FuzzyFieldEquality, DefaultFieldEquality
from fieldcompare.predicates import PredicateResult

TEST_DATA_PATH = Path(__file__).resolve().parent / Path("data")

def _get_field_from_list(name, fields_list):
    element_list = list(filter(lambda f: f.name == name, fields_list))
    assert len(element_list) == 1
    return element_list[0]

def _compare_vtk_files(file1, file2, predicate=FuzzyFieldEquality()) -> PredicateResult:
    print("Comparing vtk files")
    fields1 = read_fields(file1)
    fields2 = read_fields(file2)
    for field1 in fields1:
        field2 = _get_field_from_list(field1.name, fields2)
        print(f" -- checking field {field1.name}")
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
        TEST_DATA_PATH / Path("test_mesh.vtu"),
        TEST_DATA_PATH / Path("test_mesh.vtu"),
        DefaultFieldEquality()
    )

    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh_permutated.vtu"),
        TEST_DATA_PATH / Path("test_mesh_permutated.vtu")
    )
    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh_permutated.vtu"),
        TEST_DATA_PATH / Path("test_mesh_permutated.vtu"),
        DefaultFieldEquality()
    )

def test_vtk_files_permutated():
    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh.vtu"),
        TEST_DATA_PATH / Path("test_mesh_permutated.vtu")
    )
    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh.vtu"),
        TEST_DATA_PATH / Path("test_mesh_permutated.vtu"),
        DefaultFieldEquality()
    )

def test_vtk_files_perturbed():
    predicate = FuzzyFieldEquality()
    default_predicate = DefaultFieldEquality()
    predicate.set_relative_tolerance(1e-5)
    default_predicate.set_relative_tolerance(1e-5)

    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh.vtu"),
        TEST_DATA_PATH / Path("test_mesh_permutated_perturbed.vtu"),
        predicate
    )
    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh.vtu"),
        TEST_DATA_PATH / Path("test_mesh_permutated_perturbed.vtu"),
        default_predicate
    )

    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh_permutated.vtu"),
        TEST_DATA_PATH / Path("test_mesh_permutated_perturbed.vtu"),
        predicate
    )
    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh_permutated.vtu"),
        TEST_DATA_PATH / Path("test_mesh_permutated_perturbed.vtu"),
        default_predicate
    )

    predicate.set_relative_tolerance(1e-20)
    predicate.set_absolute_tolerance(0.0)
    default_predicate.set_relative_tolerance(1e-20)
    default_predicate.set_absolute_tolerance(0.0)
    assert not _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh.vtu"),
        TEST_DATA_PATH / Path("test_mesh_permutated_perturbed.vtu"),
        predicate
    )
    assert not _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh.vtu"),
        TEST_DATA_PATH / Path("test_mesh_permutated_perturbed.vtu"),
        default_predicate
    )

    assert not _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh_permutated.vtu"),
        TEST_DATA_PATH / Path("test_mesh_permutated_perturbed.vtu"),
        predicate
    )
    assert not _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh_permutated.vtu"),
        TEST_DATA_PATH / Path("test_mesh_permutated_perturbed.vtu"),
        default_predicate
    )

def test_non_conforming_vtk_files():
    predicate = FuzzyFieldEquality()
    default_predicate = DefaultFieldEquality()

    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_non_conforming_mesh.vtu"),
        TEST_DATA_PATH / Path("test_non_conforming_mesh.vtu"),
        predicate
    )
    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_non_conforming_mesh.vtu"),
        TEST_DATA_PATH / Path("test_non_conforming_mesh.vtu"),
        default_predicate
    )

    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_non_conforming_mesh.vtu"),
        TEST_DATA_PATH / Path("test_non_conforming_mesh_permutated.vtu"),
        predicate
    )
    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_non_conforming_mesh.vtu"),
        TEST_DATA_PATH / Path("test_non_conforming_mesh_permutated.vtu"),
        default_predicate
    )

    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_non_conforming_mesh.vtu"),
        TEST_DATA_PATH / Path("test_non_conforming_mesh_permutated_perturbed.vtu"),
        predicate
    )
    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_non_conforming_mesh.vtu"),
        TEST_DATA_PATH / Path("test_non_conforming_mesh_permutated_perturbed.vtu"),
        default_predicate
    )

    predicate.set_absolute_tolerance(1e-20)
    predicate.set_relative_tolerance(1e-20)
    default_predicate.set_absolute_tolerance(1e-20)
    default_predicate.set_relative_tolerance(1e-20)
    assert not _compare_vtk_files(
        TEST_DATA_PATH / Path("test_non_conforming_mesh.vtu"),
        TEST_DATA_PATH / Path("test_non_conforming_mesh_permutated_perturbed.vtu"),
        predicate
    )
    assert not _compare_vtk_files(
        TEST_DATA_PATH / Path("test_non_conforming_mesh.vtu"),
        TEST_DATA_PATH / Path("test_non_conforming_mesh_permutated_perturbed.vtu"),
        default_predicate
    )

if __name__ == "__main__":
    test_identical_vtk_files()
    test_vtk_files_permutated()
    test_vtk_files_perturbed()
    test_non_conforming_vtk_files()
