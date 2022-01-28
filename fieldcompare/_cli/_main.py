"""Command-line interface for fieldcompare"""

from sys import version_info
from datetime import datetime
from argparse import ArgumentParser

from fieldcompare import __version__
from fieldcompare.logging import StandardOutputLogger

from ._file_compare import _add_arguments as _file_mode_add_arguments
from ._file_compare import _run as _run_file_mode

from ._dir_compare import _add_arguments as _dir_mode_add_arguments
from ._dir_compare import _run as _run_dir_mode

def main(argv=None):
    parser = ArgumentParser(description="Compare fields in files of various formats")
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=_get_version_info(),
        help="show version information",
    )
    parser.add_argument(
        "--verbosity",
        required=False,
        default=3,
        type=int,
        help="Set the verbosity level"
    )

    sub_parsers = parser.add_subparsers(title="subcommands", dest="command", required=True)

    file_mode_parser = sub_parsers.add_parser(
        "file", help="Compare a pair of files", aliases=["f"]
    )
    _file_mode_add_arguments(file_mode_parser)
    file_mode_parser.set_defaults(func=_run_file_mode)

    dir_mode_parser = sub_parsers.add_parser(
        "dir", help="Compare the files in two directories", aliases=["d"]
    )
    _dir_mode_add_arguments(dir_mode_parser)
    dir_mode_parser.set_defaults(func=_run_dir_mode)

    args = parser.parse_args(argv)
    logger = StandardOutputLogger(verbosity_level=args.verbosity)
    return args.func(vars(args), logger)

    # TODO(Dennis): Maybe make signature as 'fieldcompare somefile --reference referencefile
    # TODO(Dennis): Change reporting mechanism in 'compare_fields' to use streams and use stdout here
    # TODO(Dennis): add value-chop option (maybe not necessary due to combo of atol/rtol)
    # TODO(Dennis): Allow comparison & predicate maps to be passed
    # TODO(Dennis): Option to treat missing references as error
    # TODO(Dennis): Put this in sub-command and add one for automatic file selection from folder


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
