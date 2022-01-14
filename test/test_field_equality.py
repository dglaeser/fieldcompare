
from context import fieldcompare

from fieldcompare import Field
from fieldcompare import ExactFieldEquality

def test_field_exact_equality():
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
