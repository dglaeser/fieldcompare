"""Test field-IO from json files"""

from os import remove
from json import dump

from pytest import raises
from context import fieldcompare
from fieldcompare import read_fields, Field
from fieldcompare import ExactFieldEquality

class TestData:
    def __init__(self):
        self._data_dict = {
            "field1": [0, 3, 8],
            "field2": [0.1, 0.5, 0.8],
            "dict": {"values": [1.0, 4.0, 10.0]},
            "some_value": 1.0
        }

    def write_json(self, filename: str) -> None:
        with open(filename, "w") as json_file:
            dump(self._data_dict, json_file)

    def check_field_equality(self, field: Field) -> bool:
        _field = Field(field.name, self._access_field_values(field.name))
        return bool(ExactFieldEquality()(_field, field))

    def _access_field_values(self, concatenated_name: str):
        keys = concatenated_name.split("/")
        values = self._data_dict[keys[0]]
        for key in keys[1:]:
            values = values[key]
        if not isinstance(values, list):
            values = [values]
        return values


def test_json_field_io():
    test_data = TestData()
    test_json_file_name = "test_json_field_io_data.json"

    test_data.write_json(test_json_file_name)
    for field in read_fields(test_json_file_name):
        assert test_data.check_field_equality(field)
    remove(test_json_file_name)

def test_invalid_json_file():
    test_data = {"field": [{"fieldarray1": [0, 1]}, {"fieldarray2": [2, 3]}]}
    test_json_file_name = "test_json_invalid_field_extraction_data.json"
    with open(test_json_file_name, "w") as json_file:
        dump(test_data, json_file)
    with raises(IOError):
        read_fields(test_json_file_name)
    remove(test_json_file_name)


if __name__ == "__main__":
    test_json_field_io()
    test_invalid_json_file()
