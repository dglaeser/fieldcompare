"""In this example, we use fieldcompare to read in fields from files and compare them"""

from os import remove
from fieldcompare import read_fields, DefaultEquality

def _write_example_csv_file() -> None:
    with open("example2.csv", "w") as csv_file:
        csv_file.write("field1,field2\n")
        csv_file.write("1.0,2.0\n")
        csv_file.write("2.0,3.0\n")

def _remove_example_csv_file() -> None:
    remove("example2.csv")


if __name__ == "__main__":
    _write_example_csv_file()

    # you may use the read_fields function to obtain the fields contained in a file
    fields = read_fields("example2.csv")

    # From the result you can get an iterable over the names of the fields
    assert sum(1 for _ in fields.field_names) == 2
    assert "field1" in fields.field_names
    assert "field2" in fields.field_names

    # Of course you can also iterate over the fields themselves
    print("Iteration over the fields")
    assert sum(1 for _ in fields) == 2
    for field in fields:
        print(f"Name -> Values: '{field.name}' -> {field.values}")

    # but you can also get the fields via their names
    print("Access via names")
    for field_name in fields.field_names:
        field = fields.get(field_name)
        print(f"Name -> Values: '{field.name}' -> {field.values}")

    # the latter can be useful e.g. when you want to compare the fields of two files for
    # equality. For instance, let's assume we were reading the same data from some other
    # source and we want to ensure that they are equal (up to fuzziness).
    reference_fields = read_fields("example2.csv")
    equal = DefaultEquality()
    for field_name in fields.field_names:
        assert equal(
            fields.get(field_name).values,
            reference_fields.get(field_name).values
        )

    _remove_example_csv_file()
