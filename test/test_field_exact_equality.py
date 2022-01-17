
from context import fieldcompare

from fieldcompare import Field
from fieldcompare import ExactFieldEquality, DefaultFieldEquality

def test_scalar_field_exact_equality():
    field1 = Field("field_name", [0, 1, 2, 3])

    check = ExactFieldEquality()
    field2 = Field(name="field_name", values=[0, 1, 2, 3])
    assert check(field1, field2)

    field2 = Field(name="wrong_name", values=[0, 1, 2, 3])
    assert not check(field1, field2)
    assert "name" in check(field1, field2).report.lower()

    field2 = Field(name="field_name", values=[0, 1, 2])
    assert not check(field1, field2)
    assert "length" in check(field1, field2).report.lower()

    field2 = Field(name="field_name", values=[0, 1, 2, 4])
    assert not check(field1, field2)
    assert "3" in check(field1, field2).report.lower()

def test_field_predicate_ignore_names_mismatch():
    field1 = Field("field1", [0, 1])
    field2 = Field("field2", [0, 1])
    check = ExactFieldEquality(ignore_names_mismatch=True)
    assert check(field1, field2)
    check = DefaultFieldEquality(ignore_names_mismatch=True)
    assert check(field1, field2)

def test_field_predicate_ignore_length_mismatch():
    field1 = Field("field1", [0, 1])
    field2 = Field("field1", [0, 1, 2])
    check = ExactFieldEquality(ignore_length_mismatch=True)
    assert check(field1, field2)
    check = DefaultFieldEquality(ignore_length_mismatch=True)
    assert check(field1, field2)

def test_vector_field_exact_equality():
    field1 = Field("field_name", [[0, 0], [1, 2]])

    check = ExactFieldEquality()
    default_check = DefaultFieldEquality()
    field2 = Field(name="field_name", values=[[0, 0], [1, 2.0]])
    assert check(field1, field2)
    assert default_check(field1, field2)

    field2 = Field(name="field_name", values=[[0, 0], [1, 2.0+1e-12]])
    assert not check(field1, field2)
    assert "2" in check(field1, field2).report.lower()
    assert not default_check(field1, field2)
    assert "2" in default_check(field1, field2).report.lower()

def test_field_exact_equality_mixed_types():
    field1 = Field("something", [0, 1, 2, True, "hello"])
    field2 = Field("something", [0, 1, 2, True, "hello"])
    check = ExactFieldEquality()
    assert check(field1, field2)
    check = DefaultFieldEquality()
    assert check(field1, field2)

    field2 = Field("something", [0, 1, 2, True, "hello22"])
    assert not check(field1, field2)
    assert not check(field1, field2)


if __name__ == "__main__":
    test_scalar_field_exact_equality()
    test_field_predicate_ignore_names_mismatch()
    test_field_predicate_ignore_length_mismatch()
    test_vector_field_exact_equality()
    test_field_exact_equality_mixed_types()
