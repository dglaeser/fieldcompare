"""Common functions used in the command-line interface"""

from typing import List
from textwrap import indent

from .._common import _style_text, TextStyle, TextColor
from ..compare import ComparisonLog, SkipLog
from ..logging import Logger
from ..field_io import read_fields


def _read_fields_from_file(filename: str, logger: Logger):
    logger.log(f"Reading fields from '{filename}'\n", verbosity_level=1)
    return read_fields(filename)


def _get_status_string(passed: bool) -> str:
    if passed:
        return _style_text("PASSED", color=TextColor.green)
    return _style_text("FAILED", color=TextColor.red)


def _style_as_warning(text: str) -> str:
    return _style_text(text, color=TextColor.yellow)


def _style_as_error(text: str) -> str:
    return _style_text(text, color=TextColor.red)


def _get_comparison_message_string(comparison_log: ComparisonLog) -> str:
    return "Comparison of the fields '{}' and '{}': {}\n".format(
        _style_text(comparison_log.result_field_name, style=TextStyle.bright),
        _style_text(comparison_log.reference_field_name, style=TextStyle.bright),
        _get_status_string(comparison_log.passed)
    )


def _get_predicate_report_string(comparison_log: ComparisonLog) -> str:
    return "Predicate: {}\nReport: {}\n".format(
        comparison_log.predicate,
        comparison_log.predicate_log
    )


def _make_list_string(missing_fields: List[str]) -> str:
    return indent("\n".join(missing_fields), "- ")


def _has_missing_result(skip_log: SkipLog) -> bool:
    return skip_log.result_field_name is None and skip_log.reference_field_name is not None


def _has_missing_reference(skip_log: SkipLog) -> bool:
    return skip_log.reference_field_name is None and skip_log.result_field_name is not None


def _get_missing_results(skip_logs: List[SkipLog]) -> List[SkipLog]:
    return list(filter(lambda log: _has_missing_result(log), skip_logs))


def _get_missing_references(skip_logs: List[SkipLog]) -> List[SkipLog]:
    return list(filter(lambda log: _has_missing_reference(log), skip_logs))

def _bool_to_exit_code(value: bool) -> int:
    return int(not value)
