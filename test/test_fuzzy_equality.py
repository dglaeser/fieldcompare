"""Test fuzzy equality checks for values/arrays"""

from pytest import raises
import numpy as np

from fieldcompare.predicates import FuzzyEquality, DefaultEquality, PredicateError, AbsoluteToleranceEstimator
from fieldcompare._numpy_utils import Array, make_array


class MockRelTolEstimator:
    def __init__(self, scaling: float) -> None:
        self._scaling = scaling

    def __call__(self, first: Array, second: Array) -> float:
        magnitude = max(np.max(first), np.max(second))
        return self._scaling*magnitude


def test_fuzzy_equality_with_scalars():
    for check in [FuzzyEquality(), DefaultEquality()]:
        assert check(1.0, 1.0)
        assert check(1.0 + 1e-20, 1.0 + 1e-20)
        assert not check(1.0, 1.0 + 1e-2)

        check.relative_tolerance = 0.1
        assert check(1.0, 1.0 + 1e-2)


def test_vector_fuzzy_equality():
    v1 = [[1.0, 1.0], [2.0, 2.0]]
    v2 = [[1.0, 1.0], [2.0 + 1e-6, 2.0 + 1e-5]]
    assert not FuzzyEquality()(v1, v2)
    assert not FuzzyEquality(rel_tol=[1e-7, 1e-4])(v1, v2)
    assert FuzzyEquality(rel_tol=[1e-5, 1e-4])(v1, v2)

    assert not FuzzyEquality(abs_tol=AbsoluteToleranceEstimator(rel_tol=1e-7))(v1, v2)
    assert FuzzyEquality(abs_tol=AbsoluteToleranceEstimator(rel_tol=1e-4))(v1, v2)

    assert not FuzzyEquality(abs_tol=AbsoluteToleranceEstimator(rel_tol=[1e-7, 1e-4]))(v1, v2)
    assert FuzzyEquality(abs_tol=AbsoluteToleranceEstimator(rel_tol=[1e-5, 1e-4]))(v1, v2)


def test_vector_fuzzy_equality_scale_per_component():
    v1 = [[1.0, 1.0e6], [2.0, 2.0e6]]
    v2 = [[1.0, 1.0e6], [2.0 + 1., 2.0e6 + 1.]]
    assert not FuzzyEquality()(v1, v2)
    assert FuzzyEquality(abs_tol=AbsoluteToleranceEstimator(rel_tol=1e-5))(v1, v2)
    assert not FuzzyEquality(abs_tol=AbsoluteToleranceEstimator(rel_tol=1e-5, use_component_magnitudes=True))(v1, v2)
    assert FuzzyEquality(abs_tol=AbsoluteToleranceEstimator(rel_tol=[2, 1e-5], use_component_magnitudes=True))(v1, v2)


def test_fuzzy_equality_with_estimated_abs_tol():
    array1 = make_array([0.0, 1e9])
    array2 = make_array([a1 + 10 for a1 in array1])
    array3 = make_array([a1 + 1 for a1 in array1])
    assert not FuzzyEquality(rel_tol=1e-9)(array1, array2)
    assert not FuzzyEquality(rel_tol=1e-9, abs_tol=AbsoluteToleranceEstimator(rel_tol=1e-9))(array1, array2)
    assert FuzzyEquality(rel_tol=1e-9, abs_tol=AbsoluteToleranceEstimator(rel_tol=1e-9))(array1, array3)


def test_fuzzy_equality_with_estimated_rel_tol():
    array1 = make_array([1.0, 1e9])
    array2 = make_array([a1 + 1e-6*max(array1) for a1 in array1])
    assert not FuzzyEquality(rel_tol=1e-6)(array1, array2)
    assert FuzzyEquality(rel_tol=MockRelTolEstimator(scaling=1e-6))(array1, array2)


def test_fuzzy_equality_with_lists():
    for check in [FuzzyEquality(), DefaultEquality()]:
        assert check([1.0, 1.0], [1.0, 1.0])
        assert check([1.0, 1.0 + 1e-20], [1.0, 1.0 + 1e-20])
        assert check([1.0, 1.0], [1.0, 1.0 + 1e-20])
        assert not check([1.0, 1.0], [1.0, 1.0 + 1e-2])

        check.relative_tolerance = 0.1
        assert check([1.0, 1.0], [1.0, 1.0 + 1e-2])


def test_fuzzy_equality_with_arrays():
    for check in [FuzzyEquality(), DefaultEquality()]:
        assert check(make_array([1.0, 1.0]), make_array([1.0, 1.0]))
        assert check(make_array([1.0, 1.0 + 1e-20]), make_array([1.0, 1.0 + 1e-20]))
        assert check(make_array([1.0, 1.0]), make_array([1.0, 1.0 + 1e-20]))
        assert not check(make_array([1.0, 1.0]), make_array([1.0, 1.0 + 1e-2]))

        check.relative_tolerance = 0.1
        assert check(make_array([1.0, 1.0]), make_array([1.0, 1.0 + 1e-2]))


def test_vector_array_fuzzy_equality():
    field1 = make_array([
        make_array([0.1, 0.2]),
        make_array([0.3, 0.5])
    ])
    field2 = make_array([
        make_array([0.1, 0.2]),
        make_array([0.3, 0.5 + 1e-6])
    ])

    for check in [FuzzyEquality(), DefaultEquality()]:
        assert not check(field1, field2)
        check.relative_tolerance = 1e-3
        assert check(field1, field2)


def test_vector_array_fuzzy_equality_mixed_shapes():
    field1 = make_array([[0.1, 0.2], [0.3]], dtype="object")
    field2 = make_array([[0.1 + 1e-6, 0.2], [0.3]], dtype="object")

    for check in [FuzzyEquality(), DefaultEquality()]:
        assert not check(field1, field2)
        check.relative_tolerance = 1e-3
        assert check(field1, field2)


def test_scalar_array_fuzzy_equality_invalid_type():
    field1 = make_array(["string1", "string2"])
    field2 = make_array(["string1", "string2"])

    with raises(PredicateError):
        check = FuzzyEquality()
        assert not check(field1, field2)
