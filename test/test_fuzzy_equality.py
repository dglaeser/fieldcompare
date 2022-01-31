"""Test fuzzy equality checks for values/arrays"""

from pytest import raises

from context import fieldcompare
from fieldcompare import Field, make_array
from fieldcompare import FuzzyEquality, DefaultEquality


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

def test_fuzzy_equality_with_field_values():
    for check in [FuzzyEquality(), DefaultEquality()]:
        field1 = Field("f1", [1.0, 1.0])
        field2 = Field("f2", [1.0, 1.0 + 1e-2])
        assert not check(field1.values, field2.values)
        check.relative_tolerance = 0.1
        assert check(field1.values, field2.values)

def test_vector_field_fuzzy_equality():
    field1 = Field("something", [[0.1, 0.2], [0.3, 0.5]])
    field2 = Field("something", [[0.1, 0.2], [0.3, 0.5 + 1e-6]])

    for check in [FuzzyEquality(), DefaultEquality()]:
        assert not check(field1.values, field2.values)
        check.relative_tolerance = 1e-3
        assert check(field1.values, field2.values)

def test_vector_field_fuzzy_equality_mixed_shapes():
    field1 = Field("something", make_array([[0.1, 0.2], [0.3]], dtype="object"))
    field2 = Field("something", make_array([[0.1 + 1e-6, 0.2], [0.3]], dtype="object"))

    for check in [FuzzyEquality(), DefaultEquality()]:
        assert not check(field1.values, field2.values)
        check.relative_tolerance = 1e-3
        assert check(field1.values, field2.values)

def test_scalar_field_fuzzy_equality_invalid_type():
    field1 = Field("something", ["string1", "string2"])
    field2 = Field("something", ["string1", "string2"])

    with raises(ValueError):
        check = FuzzyEquality()
        assert not check(field1.values, field2.values)

if __name__ == "__main__":
    test_fuzzy_equality_with_scalars()
    test_fuzzy_equality_with_lists()
    test_fuzzy_equality_with_arrays()
    test_fuzzy_equality_with_field_values()
    test_vector_field_fuzzy_equality()
    test_vector_field_fuzzy_equality_mixed_shapes()
    test_scalar_field_fuzzy_equality_invalid_type()
