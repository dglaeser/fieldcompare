"""Command-line interface for fieldcompare"""

from sys import version_info
from datetime import datetime
from argparse import ArgumentParser

from fieldcompare import __version__

from ._logger import CLILogger
from ._file_mode import _add_arguments as _file_mode_add_arguments
from ._file_mode import _run as _run_file_mode

from ._dir_mode import _add_arguments as _dir_mode_add_arguments
from ._dir_mode import _run as _run_dir_mode


def main(argv=None, logger: CLILogger = CLILogger()):
    parser = ArgumentParser(description="Compare fields in files of various formats")
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=_get_version_info(),
        help="show version information",
    )

    sub_parsers = parser.add_subparsers(title="subcommands", dest="command", required=True)
    _add_file_mode_parser(sub_parsers)
    _add_directory_mode_parser(sub_parsers)

    args = parser.parse_args(argv)
    return args.func(vars(args), logger)


def _add_file_mode_parser(sub_parsers) -> None:
    file_mode_parser = sub_parsers.add_parser("file", help="Compare a pair of files", aliases=["f"])
    _file_mode_add_arguments(file_mode_parser)
    file_mode_parser.set_defaults(func=_run_file_mode)


def _add_directory_mode_parser(sub_parsers) -> None:
    dir_mode_parser = sub_parsers.add_parser(
        "dir", help="Compare the files in two directories", aliases=["d"]
    )
    _dir_mode_add_arguments(dir_mode_parser)
    dir_mode_parser.set_defaults(func=_run_dir_mode)


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
