"""Test equality of fields read from vtk files"""

from pathlib import Path
from pytest import raises

from context import fieldcompare
from fieldcompare import predicates, read_fields
from _common import FuzzyFieldEquality, DefaultFieldEquality

TEST_DATA_PATH = Path(__file__).resolve().parent / Path("data")

def _get_field_from_list(name, fields_list):
    element_list = list(filter(lambda f: f.name == name, fields_list))
    assert len(element_list) == 1
    return element_list[0]

def _compare_vtk_files(file1,
                       file2,
                       predicate=FuzzyFieldEquality(),
                       remove_ghost_points: bool = True) -> bool:
    print("Comparing vtk files")
    fields1 = read_fields(file1, remove_ghost_points)
    fields2 = read_fields(file2, remove_ghost_points)
    for field1 in fields1:
        field2 = _get_field_from_list(field1.name, fields2)
        print(f" -- checking field {field1.name}")
        return predicate(field1, field2)
    return True


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

def test_vtk_with_ghost_points():
    predicate = FuzzyFieldEquality()
    default_predicate = DefaultFieldEquality()

    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_non_conforming_mesh.vtu"),
        TEST_DATA_PATH / Path("test_non_conforming_mesh_with_ghost_points.vtu"),
        predicate
    )
    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_non_conforming_mesh.vtu"),
        TEST_DATA_PATH / Path("test_non_conforming_mesh_with_ghost_points.vtu"),
        default_predicate
    )

    with raises(IOError):
        _compare_vtk_files(
            TEST_DATA_PATH / Path("test_non_conforming_mesh.vtu"),
            TEST_DATA_PATH / Path("test_non_conforming_mesh_with_ghost_points.vtu"),
            predicate,
            remove_ghost_points=False
        )

    with raises(IOError):
        _compare_vtk_files(
            TEST_DATA_PATH / Path("test_non_conforming_mesh.vtu"),
            TEST_DATA_PATH / Path("test_non_conforming_mesh_with_ghost_points.vtu"),
            default_predicate,
            remove_ghost_points=False
        )

if __name__ == "__main__":
    test_identical_vtk_files()
    test_vtk_files_permutated()
    test_vtk_files_perturbed()
    test_non_conforming_vtk_files()
