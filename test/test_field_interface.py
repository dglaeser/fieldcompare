"""Test the field interface class"""

from context import fieldcompare
from fieldcompare import Field, FieldInterface

class CustomField(FieldInterface):
    @property
    def name(self) -> str:
        return "custom"

    @property
    def values(self) -> list:
        return [0, 1, 2, 3]

@FieldInterface.register
class NonInheritingField:
    @property
    def name(self) -> str:
        return "non_inheriting"

    @property
    def values(self) -> list:
        return [0, 1, 2, 3]

def check_if_field_interface(obj: FieldInterface) -> bool:
    return isinstance(obj, FieldInterface)


def test_field_construction():
    field1 = Field("field_name", [0, 1, 2, 3])
    field2 = Field(name="field_name", values=[0, 1, 2, 3])
    for field in field1, field2:
        assert field.name == "field_name"
        assert all(a == b for a, b in zip(field.values, [0, 1, 2, 3]))

def test_field_interface():
    assert check_if_field_interface(Field("some_field", [0, 1, 2]))
    assert check_if_field_interface(CustomField())
    assert check_if_field_interface(NonInheritingField())
    assert not check_if_field_interface(float())

if __name__ == "__main__":
    test_field_construction()
    test_field_interface()
