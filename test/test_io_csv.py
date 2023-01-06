"""Test field-IO from csv files"""

from io import StringIO

from fieldcompare.predicates import ExactEquality
from fieldcompare.tabular import Table, transform
from fieldcompare.io import CSVFieldReader


def _as_string_stream(data: dict, add_names: bool = True, delimiter=",") -> StringIO:
    stream = StringIO()
    if add_names:
        stream.write(delimiter.join(data.keys()) + "\n")
    values = list(data.values())
    num_rows = len(values[0])
    for row_idx in range(num_rows):
        stream.write(delimiter.join(str(values[col][row_idx]) for col in range(len(values))) + "\n")
    stream.seek(0)
    return stream


def get_reference_data():
    return {
        "int_field": [0, 3, 8, 10],
        "float_field": [1.0, 4.0, 10.0, 12],
        "str_field": ["value0", "value1", "value2", "value3"]
    }


def test_csv_field_extraction():
    reference_data = get_reference_data()
    stream = _as_string_stream(reference_data)
    fields = CSVFieldReader(delimiter=",", use_names=True).read(stream)

    for field in fields:
        assert reference_data.get(field.name) is not None
        assert ExactEquality()(
            field.values,
            reference_data[field.name]
        )


def test_csv_field_extraction_single_dtype():
    reference_data = {
        f"float_field_{i}": get_reference_data()["float_field"]
        for i in range(3)
    }
    stream = _as_string_stream(reference_data, add_names=False)
    fields = CSVFieldReader(delimiter=",", use_names=False, skip_rows=0).read(stream)

    assert all(
        ExactEquality()(
            field.values,
            get_reference_data()["float_field"]
        ) for field in fields
    )


def test_csv_field_extraction_deduced_delimiters_and_headers():
    reference_data = get_reference_data()
    for delimiter in [",", ";", " "]:
        for use_names in [True, False]:
            stream = _as_string_stream(reference_data, delimiter=delimiter, add_names=use_names)
            fields = CSVFieldReader().read(stream)

            for field in fields:
                assert any(
                    ExactEquality()(
                        field.values,
                        reference_data[ref]
                    ) for ref in reference_data
                )


def test_csv_field_extraction_no_names():
    reference_data = get_reference_data()
    stream = _as_string_stream(reference_data)
    fields = CSVFieldReader(delimiter=",", use_names=False, skip_rows=1).read(stream)

    ref_field_names = list(reference_data.keys())
    for i, field in enumerate(fields):
        assert ExactEquality()(
            field.values,
            reference_data[ref_field_names[i]]
        )


def test_csv_field_permutation():
    reference_data = get_reference_data()
    num_rows = len(reference_data[list(reference_data.keys())[0]])

    stream = _as_string_stream(reference_data)
    fields = CSVFieldReader(delimiter=",").read(stream)
    fields_permuted = transform(
        fields,
        lambda _: Table(
            num_rows=num_rows,
            idx_map=list(reversed(list(range(num_rows))))
        )
    )

    for field in fields_permuted:
        assert reference_data.get(field.name) is not None
        assert ExactEquality()(
            field.values,
            list(reversed(reference_data[field.name]))
        )
