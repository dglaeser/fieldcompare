"""Test fuzzy equality checks for values/arrays"""

from pytest import raises

from fieldcompare.predicates import FuzzyEquality, DefaultEquality, PredicateError
from fieldcompare._numpy_utils import make_array

def test_fuzzy_equality_with_scalars():
    for check in [FuzzyEquality(), DefaultEquality()]:
        assert check(1.0, 1.0)
        assert check(1.0 + 1e-20, 1.0 + 1e-20)
        assert not check(1.0, 1.0 + 1e-2)

        check.relative_tolerance = 0.1
        assert check(1.0, 1.0 + 1e-2)


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
