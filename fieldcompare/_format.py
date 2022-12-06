"""Logging output formatting helpers"""

from typing import List, Optional
from textwrap import indent
from enum import Enum

import colorama
colorama.init()


class _AnsiiColorBackend:
    def __init__(self, use_colors=True, use_styles=True):
        self._reset_key = "reset_all"
        self._setup_color_map(use_colors)
        self._setup_style_map(use_styles)

    def make_colored(self, text: str, color, style) -> str:
        if color is not None:
            text = self._color_map[str(color).lower()] + text
        if style is not None:
            text = self._style_map[str(style).lower()] + text
        if color is not None or style is not None:
            text = text + self._style_map[self._reset_key]
        return text

    def remove_color_codes(self, text: str) -> str:
        for _, code in self._color_map.items():
            text = text.replace(code, "")
        for _, code in self._style_map.items():
            text = text.replace(code, "")
        return text

    def _setup_color_map(self, use_colors: bool) -> None:
        self._color_map: dict = {}
        for name in dir(colorama.Fore):
            if not name.startswith('_'):
                self._color_map[name.lower()] = getattr(colorama.Fore, name) if use_colors else ""

    def _setup_style_map(self, use_styles: bool) -> None:
        self._style_map: dict = {}
        for name in dir(colorama.Style):
            if not name.startswith('_'):
                self._style_map[name.lower()] = getattr(colorama.Style, name) if use_styles else ""
        assert self._reset_key in self._style_map

_COLOR_BACKEND = _AnsiiColorBackend()


class TextColor(Enum):
    red = "red"
    green = "green"
    blue = "blue"
    magenta = "magenta"
    yellow = "yellow"

    def __str__(self) -> str:
        return str(self.value)


class TextStyle(Enum):
    dim = "DIM"
    normal = "NORMAL"
    bright = "BRIGHT"

    def __str__(self) -> str:
        return str(self.value)


def make_colored(text: str,
                 color: Optional[TextColor] = None,
                 style: Optional[TextStyle] = None) -> str:
    return _COLOR_BACKEND.make_colored(text, color, style)  # type: ignore


def remove_color_codes(text: str) -> str:
    return _COLOR_BACKEND.remove_color_codes(text)


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


def highlighted(text: str) -> str:
    return make_colored(text, style=TextStyle.bright)


def make_list_string(names: List[str]) -> str:
    return indent("\n".join(names), "- ")


def make_indented_list_string(names: List[str]) -> str:
    return indent(make_list_string(names), "  ")
