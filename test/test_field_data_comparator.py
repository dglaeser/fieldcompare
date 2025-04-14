# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations
from typing import Iterable, Iterator
from random import Random
from pathlib import Path
from io import StringIO
from functools import partial

from pytest import raises

from fieldcompare import FieldDataComparator
from fieldcompare import protocols

from fieldcompare.io import read
from fieldcompare.mesh import protocols as mesh_protocols
from fieldcompare.mesh import sort, sort_cells, sort_points, MeshFieldsComparator, Mesh, CellTypes, CellType
from fieldcompare.predicates import DefaultEquality, FuzzyEquality
from fieldcompare._numpy_utils import Array, make_array, make_zeros
from fieldcompare._field import Field

TEST_DATA_PATH = Path(__file__).resolve().parent / Path("data")

def _compare_vtk_files(file1,
                       file2,
                       predicate=FuzzyEquality(),
                       remove_ghost_points: bool = True) -> bool:
    print("Comparing vtk files")
    fields1 = read(file1)
    fields2 = read(file2)
    assert isinstance(fields1, mesh_protocols.MeshFields)
    assert isinstance(fields2, mesh_protocols.MeshFields)
    if remove_ghost_points:
        fields1 = sort(fields1)
        fields2 = sort(fields2)
    else:
        fields1 = sort_cells(sort_points(fields1))
        fields2 = sort_cells(sort_points(fields2))
    assert isinstance(fields1, mesh_protocols.MeshFields)
    assert isinstance(fields2, mesh_protocols.MeshFields)
    fields1.domain.set_tolerances(abs_tol=predicate.absolute_tolerance, rel_tol=predicate.relative_tolerance)
    fields2.domain.set_tolerances(abs_tol=predicate.absolute_tolerance, rel_tol=predicate.relative_tolerance)
    result = FieldDataComparator(fields1, fields2)(
        predicate_selector=lambda _, __: predicate,
        fieldcomp_callback=lambda c: print(f"{c.name}: {c.status}")
    )
    print(f"Domain-Check = {result.domain_equality_check}")
    return bool(result)


class MockMeshFields(mesh_protocols.MeshFields):
    def __init__(self,
                 num_fields: int = 1,
                 perturbation: float = 0.0,
                 space_dimension: int = 2) -> None:
        assert space_dimension >= 2
        self._random_instance = Random(1234)
        self._perturbation = perturbation
        self._space_dimension = space_dimension
        self._num_points = 3
        self._fields = list(
            Field(f"f_{i}", self._test_array(i))
            for i in range(num_fields)
        )

    @property
    def domain(self) -> Mesh:
        return Mesh(
            points=make_array([
                [float(i), float(i)] + [0.0 for _ in range(self._space_dimension - 2)]
                for i in range(self._num_points)
            ]),
            connectivity=[(
                CellTypes.line, [[i, i+1] for i in range(self._num_points - 1)]
            )]
        )

    @property
    def point_fields(self) -> Iterable[Field]:
        return self._fields

    @property
    def cell_fields(self) -> Iterable[Field]:
        return make_array([])

    @property
    def cell_fields_types(self) -> Iterable[tuple[Field, CellType]]:
        return make_array([])

    def __iter__(self) -> Iterator[Field]:
        return iter(self._fields)

    def transformed(self, _) -> Mesh:
        raise NotImplementedError("Permutation of mock field data")

    def diff_to(self, _: MockMeshFields) -> protocols.FieldData:
        raise NotImplementedError("Diff computation")

    def _test_array(self, i: int) -> Array:
        def _random(base_value: float) -> float:
            return base_value + self._random_instance.uniform(0.0, self._perturbation)

        if i % 3 == 0:  # make scalar field
            return make_array([_random(42.0 + float(i)) for i in range(self._num_points)])
        if i % 3 == 1:  # make vector field
            result = make_zeros(shape=(self._num_points, self._space_dimension), dtype=float)
            result[:, :2] = _random(42.0)
            return result
        # make tensor field
        result = make_zeros(shape=(self._num_points, self._space_dimension, self._space_dimension), dtype=float)
        result[:, :2, :2] = _random(42.0)
        return result


def get_number_of_lines(msg: str) -> int:
    return len(list(msg.strip("\n").split("\n")))


def compare_and_stream_output(source, reference, comparator=FieldDataComparator):
    out_stream = StringIO()
    comparison = comparator(source, reference)
    suite = comparison(
        predicate_selector=lambda _, __: DefaultEquality(),
        fieldcomp_callback=lambda p: out_stream.write("--\n")
    )
    return suite, out_stream.getvalue()


def test_field_data_comparison():
    source = MockMeshFields()
    reference = MockMeshFields()
    suite, stdout = compare_and_stream_output(source, reference)

    assert suite
    assert len(list(suite)) == 1
    assert len(list(suite.passed)) == 1
    assert len(list(suite.failed)) == 0
    assert len(list(suite.skipped)) == 0
    assert get_number_of_lines(stdout) == 1


def test_mesh_field_data_comparison():
    source = MockMeshFields(4, space_dimension=2)
    reference = MockMeshFields(4, space_dimension=3)
    suite, _ = compare_and_stream_output(
        source, reference, partial(MeshFieldsComparator, disable_space_dimension_matching=True)
    )
    assert not suite
    suite, _ = compare_and_stream_output(source, reference, MeshFieldsComparator)

    assert suite
    assert len(list(suite)) == 4
    assert len(list(suite.passed)) == 4
    assert len(list(suite.failed)) == 0
    assert len(list(suite.skipped)) == 0


def test_field_data_comparison_missing_source():
    source = MockMeshFields()
    reference = MockMeshFields(num_fields=2)
    suite, stdout = compare_and_stream_output(source, reference)

    assert not suite
    assert len(list(suite)) == 2
    assert len(list(suite.passed)) == 1
    assert len(list(suite.failed)) == 1
    assert len(list(suite.skipped)) == 0
    assert get_number_of_lines(stdout) == 1


def test_field_data_comparison_missing_reference():
    source = MockMeshFields(num_fields=2)
    reference = MockMeshFields(num_fields=1)
    suite, stdout = compare_and_stream_output(source, reference)

    assert not suite
    assert len(list(suite)) == 2
    assert len(list(suite.passed)) == 1
    assert len(list(suite.failed)) == 1
    assert len(list(suite.skipped)) == 0
    assert get_number_of_lines(stdout) == 1


def test_failing_field_data_comparison():
    source = MockMeshFields(num_fields=1)
    reference = MockMeshFields(num_fields=1, perturbation=0.01)
    suite, stdout = compare_and_stream_output(source, reference)

    assert not suite
    assert len(list(suite)) == 1
    assert len(list(suite.passed)) == 0
    assert len(list(suite.failed)) == 1
    assert len(list(suite.skipped)) == 0
    assert get_number_of_lines(stdout) == 1


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
    predicate.absolute_tolerance = 1e-9
    default_predicate.relative_tolerance = 1e-5
    default_predicate.absolute_tolerance = 1e-9

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
    predicate.absolute_tolerance = 1e-9
    default_predicate.absolute_tolerance = 1e-9

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
