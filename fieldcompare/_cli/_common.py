"""Common functions used in the command-line interface"""

from typing import List
from textwrap import indent

from ..colors import make_colored, TextColor
from ..logging import Logger, ModifiedVerbosityLoggerFacade, IndentedLoggingFacade
from ..field_io import read_fields


def _read_fields_from_file(filename: str, logger: Logger):
    logger.log(f"Reading fields from '{filename}'\n", verbosity_level=1)
    low_verbosity_logger = ModifiedVerbosityLoggerFacade(logger, verbosity_change=-2)
    file_io_logger = IndentedLoggingFacade(low_verbosity_logger, " "*4)
    return read_fields(filename, logger=file_io_logger)


def _get_status_string(passed: bool) -> str:
    if passed:
        return make_colored("PASSED", color=TextColor.green)
    return make_colored("FAILED", color=TextColor.red)


def _style_as_warning(text: str) -> str:
    return make_colored(text, color=TextColor.yellow)


def _style_as_error(text: str) -> str:
    return make_colored(text, color=TextColor.red)


def _make_list_string(missing_fields: List[str]) -> str:
    return indent("\n".join(missing_fields), "- ")


def _bool_to_exit_code(value: bool) -> int:
    return int(not value)
