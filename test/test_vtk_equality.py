"""Test equality of fields read from vtk files"""

from pathlib import Path
from pytest import raises

from fieldcompare.mesh import read, permutations, sort
from fieldcompare.predicates import FuzzyEquality, DefaultEquality
from fieldcompare import FieldDataComparison


TEST_DATA_PATH = Path(__file__).resolve().parent / Path("data")


def _get_field_from_list(name, fields_list):
    element_list = list(filter(lambda f: f.name == name, fields_list))
    assert len(element_list) == 1
    return element_list[0]


def _compare_vtk_files(file1,
                       file2,
                       predicate=FuzzyEquality(),
                       remove_ghost_points: bool = True) -> bool:
    print("Comparing vtk files")
    fields1 = read(file1)
    fields2 = read(file2)
    if remove_ghost_points:
        fields1 = sort(fields1)
        fields2 = sort(fields2)
    else:
        fields1 = fields1.permuted(permutations.sort_points).permuted(permutations.sort_cells)
        fields2 = fields2.permuted(permutations.sort_points).permuted(permutations.sort_cells)
    fields1.domain.set_tolerances(abs_tol=predicate.absolute_tolerance, rel_tol=predicate.relative_tolerance)
    fields2.domain.set_tolerances(abs_tol=predicate.absolute_tolerance, rel_tol=predicate.relative_tolerance)
    result = FieldDataComparison(fields1, fields2)(
        predicate_selector=lambda _, __: predicate,
        fieldcomp_callback=lambda c: print(f"{c.name}: {c.status}")
    )
    print(f"Domain-Check = {result.domain_equality_check}")
    return bool(result)


def test_identical_vtk_files():
    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh.vtu"),
        TEST_DATA_PATH / Path("test_mesh.vtu")
    )
    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh.vtu"),
        TEST_DATA_PATH / Path("test_mesh.vtu"),
        DefaultEquality()
    )

    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh_permutated.vtu"),
        TEST_DATA_PATH / Path("test_mesh_permutated.vtu")
    )
    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh_permutated.vtu"),
        TEST_DATA_PATH / Path("test_mesh_permutated.vtu"),
        DefaultEquality()
    )


def test_vtk_files_permutated():
    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh.vtu"),
        TEST_DATA_PATH / Path("test_mesh_permutated.vtu")
    )
    assert _compare_vtk_files(
        TEST_DATA_PATH / Path("test_mesh.vtu"),
        TEST_DATA_PATH / Path("test_mesh_permutated.vtu"),
        DefaultEquality()
    )


def test_vtk_files_perturbed():
    predicate = FuzzyEquality()
    default_predicate = DefaultEquality()
    predicate.relative_tolerance = 1e-5
    default_predicate.relative_tolerance = 1e-5

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

    predicate.relative_tolerance = 1e-20
    predicate.absolute_tolerance = 0.0
    default_predicate.relative_tolerance = 1e-20
    default_predicate.absolute_tolerance = 0.0
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
    predicate = FuzzyEquality()
    default_predicate = DefaultEquality()

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

    predicate.absolute_tolerance = 1e-20
    predicate.relative_tolerance = 1e-20
    default_predicate.absolute_tolerance = 1e-20
    default_predicate.relative_tolerance = 1e-20
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
    predicate = FuzzyEquality()
    default_predicate = DefaultEquality()

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

    with raises(ValueError):
        _compare_vtk_files(
            TEST_DATA_PATH / Path("test_non_conforming_mesh.vtu"),
            TEST_DATA_PATH / Path("test_non_conforming_mesh_with_ghost_points.vtu"),
            predicate,
            remove_ghost_points=False
        )

    with raises(ValueError):
        _compare_vtk_files(
            TEST_DATA_PATH / Path("test_non_conforming_mesh.vtu"),
            TEST_DATA_PATH / Path("test_non_conforming_mesh_with_ghost_points.vtu"),
            default_predicate,
            remove_ghost_points=False
        )
