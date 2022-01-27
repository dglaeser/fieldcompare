"""Command-line interface for fieldcompare"""

from sys import version_info
from datetime import datetime
from argparse import ArgumentParser

from fieldcompare import __version__
from fieldcompare.field_io import read_fields
from fieldcompare.compare import compare_matching_fields_equal

def main(argv=None):
    parser = ArgumentParser(description="Compare fields in files of various formats")
    parser.add_argument("file", help="The files to compare against a reference")
    parser.add_argument("reference", help="The reference file used for comparison")
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=_get_version_info(),
        help="show version information",
    )
    parser.add_argument(
        "--verbosity",
        required=False,
        default=1,
        type=int,
        help="Set the verbosity level"
    )
    args = vars(parser.parse_args(argv))

    # TODO(Dennis): Maybe make signature as 'fieldcompare somefile --reference referencefile
    # TODO(Dennis): Change reporting mechanism in 'compare_fields' to use streams and use stdout here
    # TODO(Dennis): add value-chop option (maybe not necessary due to combo of atol/rtol)
    # TODO(Dennis): Allow comparison & predicate maps to be passed
    # TODO(Dennis): Option to treat missing references as error
    # TODO(Dennis): Put this in sub-command and add one for automatic file selection from folder

    fields1 = _read_file(args["file"])
    fields2 = _read_file(args["reference"])
    result, _ = compare_matching_fields_equal(fields1, fields2)
    return int(not bool(result))


def _read_file(filename: str):
    print(f"Reading fields from '{filename}'")
    return read_fields(filename)


def _get_version_info() -> str:
    python_version = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
    version = __version__ if __version__ != "unknown" else "(unknown version)"
    return "\n".join([
        f"fieldcompare {version} [Python {python_version}]",
        f"Copyright (c) {_get_development_years_string()} Dennis Gläser et al.",
    ])


def _get_development_years_string() -> str:
    begin = _get_development_begin_year()
    current = _get_current_year()
    if current > begin:
        return f"{_get_development_begin_year()}-{_get_current_year()}"
    return f"{current}"


def _get_current_year() -> int:
    return datetime.now().year


def _get_development_begin_year() -> int:
    return 2022
