"""Test fuzzy equality checks on fields"""

from pytest import raises
from context import fieldcompare

from fieldcompare import Field, make_array
from fieldcompare import FuzzyFieldEquality, DefaultFieldEquality

def test_scalar_field_fuzzy_equality():
    field1 = Field("something", [0.1, 0.2, 0.3])
    field2 = Field("something", [0.1 + 1e-6, 0.2, 0.3])

    check = FuzzyFieldEquality()
    assert not check(field1, field2)

    check.set_relative_tolerance(1e-3)
    assert check(field1, field2)

def test_vector_field_fuzzy_equality():
    field1 = Field("something", [[0.1, 0.2], [0.3, 0.5]])
    field2 = Field("something", [[0.1, 0.2], [0.3, 0.5 + 1e-6]])

    check = FuzzyFieldEquality()
    default_check = DefaultFieldEquality()

    assert not check(field1, field2)
    assert not default_check(field1, field2)

    check.set_relative_tolerance(1e-3)
    default_check.set_relative_tolerance(1e-3)
    assert check(field1, field2)
    assert default_check(field1, field2)

def test_vector_field_fuzzy_equality_mixed_shapes():
    field1 = Field("something", make_array([[0.1, 0.2], [0.3]], dtype="object"))
    field2 = Field("something", make_array([[0.1 + 1e-6, 0.2], [0.3]], dtype="object"))

    check = FuzzyFieldEquality()
    assert not check(field1, field2)

    check.set_relative_tolerance(1e-3)
    assert check(field1, field2)


def test_scalar_field_fuzzy_equality_invalid_type():
    field1 = Field("something", ["string1", "string2"])
    field2 = Field("something", ["string1", "string2"])

    with raises(ValueError):
        check = FuzzyFieldEquality()
        assert not check(field1, field2)

if __name__ == "__main__":
    test_scalar_field_fuzzy_equality()
    test_vector_field_fuzzy_equality()
    test_vector_field_fuzzy_equality_mixed_shapes()
    test_scalar_field_fuzzy_equality_invalid_type()
