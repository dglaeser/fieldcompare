"""Test field-IO from csv files"""

from os import remove
from csv import writer

from context import fieldcompare
from fieldcompare import read_fields
from fieldcompare import Field, ExactEquality
from _common import ExactFieldEquality


def _write_fields_to_csv_no_names(filename: str, values) -> None:
    with open(filename, "w") as csv_file:
        csv_writer = writer(csv_file)
        num_cols = len(values[0])
        assert all(len(vals) == num_cols for vals in values)
        for i in range(num_cols):
            csv_writer.writerow(vals[i] for vals in values)

def _write_fields_to_csv(filename: str, names, values) -> None:
    with open(filename, "w") as csv_file:
        csv_writer = writer(csv_file)
        csv_writer.writerow(names)

        num_cols = len(values[0])
        assert all(len(vals) == num_cols for vals in values)
        for i in range(num_cols):
            csv_writer.writerow(vals[i] for vals in values)

def get_reference_data():
    return {
        "int_field": {"values": [0, 3, 8]},
        "float_field": {"values": [1.0, 4.0, 10.0]},
        "str_field": {"values": ["value0", "value1", "value2"]}
    }


def test_csv_field_extraction():
    ref_data = get_reference_data()
    test_csv_file_name = "test_csv_field_extraction_data.csv"
    _write_fields_to_csv(
        test_csv_file_name,
        ref_data.keys(),
        [d["values"] for d in ref_data.values()]
    )

    for field in read_fields(test_csv_file_name):
        assert ref_data.get(field.name) is not None
        assert ExactFieldEquality()(
            field,
            Field(field.name, ref_data.get(field.name)["values"])
        )
    remove(test_csv_file_name)


def test_csv_field_extraction_no_names():
    ref_data = get_reference_data()
    test_csv_file_name = "test_csv_field_extraction_data_no_names.csv"
    _write_fields_to_csv_no_names(
        test_csv_file_name,
        [d["values"] for d in ref_data.values()]
    )

    for field in read_fields(test_csv_file_name):
        assert any(
            ExactFieldEquality(require_equal_names=False)(
                field,
                Field(field_name, ref_data.get(field_name)["values"])
            ) for field_name in ref_data.keys()
        )
    remove(test_csv_file_name)

if __name__ == "__main__":
    test_csv_field_extraction()
    test_csv_field_extraction_no_names()
