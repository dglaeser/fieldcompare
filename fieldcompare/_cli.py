"""Command-line interface for fieldcompare"""

from sys import version_info
from datetime import datetime
from argparse import ArgumentParser
from textwrap import indent

from fieldcompare import __version__
from fieldcompare._common import _style_text, TextStyle, TextColor
from fieldcompare.field_io import read_fields
from fieldcompare.compare import compare_matching_fields_equal, ComparisonLog
from fieldcompare.logging import Logger, StandardOutputLogger


def _get_status_string(passed: bool) -> str:
    if passed:
        return _style_text("PASSED", color=TextColor.green)
    return _style_text("FAILED", color=TextColor.red)

def _get_comparison_message_string(comparison_log: ComparisonLog) -> str:
    return "Comparison of the fields '{}' and '{}': {}\n".format(
        _style_text(comparison_log.result_field_name, style=TextStyle.bright),
        _style_text(comparison_log.reference_field_name, style=TextStyle.bright),
        _get_status_string(comparison_log.passed)
    )

def _get_predicate_report(comparison_log: ComparisonLog) -> str:
    return "Predicate: {}\nReport: {}\n".format(
        comparison_log.predicate,
        comparison_log.predicate_log
    )


class ComparisonLogCallBack:
    def __init__(self, logger: Logger) -> None:
        self._logger = logger

    def __call__(self, comparison_log: ComparisonLog) -> None:
        self._logger.log(_get_comparison_message_string(comparison_log), verbosity_level=1)
        self._logger.log(
            indent(_get_predicate_report(comparison_log), " -- "),
            verbosity_level=2
        )


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
        default=2,
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

    logger = StandardOutputLogger(verbosity_level=args["verbosity"])
    fields1 = _read_file(args["file"], logger)
    fields2 = _read_file(args["reference"], logger)
    log_call_back = ComparisonLogCallBack(logger)
    result, _ = compare_matching_fields_equal(fields1, fields2, log_call_back)
    return int(not bool(result))


def _read_file(filename: str, logger):
    logger.log(f"Reading fields from '{filename}'\n", verbosity_level=1)
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
