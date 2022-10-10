"""Logging output formatting helpers"""

from typing import List
from textwrap import indent

from ._colors import make_colored, TextColor, TextStyle


def get_status_string(passed: bool) -> str:
    if passed:
        return as_success("PASSED")
    return as_error("FAILED")


def as_warning(text: str) -> str:
    return make_colored(text, color=TextColor.yellow)


def as_error(text: str) -> str:
    return make_colored(text, color=TextColor.red)


def as_success(text: str) -> str:
    return make_colored(text, color=TextColor.green)


def highlight(text: str) -> str:
    return make_colored(text, style=TextStyle.bright)


def make_list_string(names: List[str]) -> str:
    return indent("\n".join(names), "- ")


def make_indented_list_string(names: List[str]) -> str:
    return indent(make_list_string(names), "  ")
