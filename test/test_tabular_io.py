# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

from os import walk, remove
from os.path import splitext
from pathlib import Path

from fieldcompare.io import read, read_field_data, write
from fieldcompare.protocols import FieldData
from fieldcompare import FieldDataComparator


def _get_file_name_with_extension(ext: str) -> str:
    test_data = Path(__file__).resolve().parent / Path("data")
    for _, _, files in walk(str(test_data)):
        for file in files:
            if splitext(file)[1] == ext:
                return str(test_data / Path(file))
    raise FileNotFoundError(f"No file found with extension {ext}")


def test_csv_field_reading():
    _ = read(_get_file_name_with_extension(".csv"))


def test_tabular_fields_output():
    fields = read_field_data(_get_file_name_with_extension(".csv"))
    write(fields, "tmp_tables")
    written_fields = read_field_data("tmp_tables.csv")
    assert FieldDataComparator(fields, written_fields)()
    remove("tmp_tables.csv")
