
from context import fieldcompare

from fieldcompare import Field
from fieldcompare import FuzzyFieldEquality

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
    assert not check(field1, field2)

    check.set_relative_tolerance(1e-3)
    assert check(field1, field2)

if __name__ == "__main__":
    test_scalar_field_fuzzy_equality()
    test_vector_field_fuzzy_equality()
