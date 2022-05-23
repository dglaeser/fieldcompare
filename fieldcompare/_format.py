"""Logging output formatting helpers"""

from typing import List
from textwrap import indent

from ._colors import make_colored, TextColor


def get_status_string(passed: bool) -> str:
    if passed:
        return make_colored("PASSED", color=TextColor.green)
    return make_colored("FAILED", color=TextColor.red)


def as_warning(text: str) -> str:
    return make_colored(text, color=TextColor.yellow)


def as_error(text: str) -> str:
    return make_colored(text, color=TextColor.red)


def make_list_string(missing_fields: List[str]) -> str:
    return indent("\n".join(missing_fields), "- ")
