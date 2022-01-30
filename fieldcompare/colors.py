"""Wrap text in escape characters to produce colored output on terminals"""

from warnings import warn
from enum import Enum
from contextlib import contextmanager
from copy import deepcopy

try:
    import colorama
    colorama.init()
    _COLORAMA_FOUND = True
except ImportError:
    _COLORAMA_FOUND = False


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


class _NullColorBackend:
    def make_colored(self, text: str, color, style) -> str:
        return text


_COLOR_BACKEND = _AnsiiColorBackend() if _COLORAMA_FOUND else _NullColorBackend()

def deactivate_colored_output() -> None:
    global _COLOR_BACKEND
    _COLOR_BACKEND = _NullColorBackend()

def activate_colored_output() -> None:
    if not _COLORAMA_FOUND:
        warn(RuntimeWarning("Cannot activate colored output, colorama package not found"))
    else:
        global _COLOR_BACKEND
        _COLOR_BACKEND = _AnsiiColorBackend()

@contextmanager
def text_color_options(use_colors=True, use_styles=True):
    global _COLOR_BACKEND
    backend = deepcopy(_COLOR_BACKEND)
    if not _COLORAMA_FOUND:
        if use_styles or use_styles:
            warn(RuntimeWarning("Cannot use colored options, colorama package not found"))
        deactivate_colored_output()
    else:
        activate_colored_output()
        _COLOR_BACKEND = _AnsiiColorBackend(use_colors, use_styles)

    try:
        yield {"use_colors": use_colors, "use_styles": use_styles}
    finally:
        _COLOR_BACKEND = backend


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
                 color: TextColor = None,
                 style: TextStyle = None) -> str:
    return _COLOR_BACKEND.make_colored(text, color, style)
