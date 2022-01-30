"""Wrap text in escape characters to produce colored output on terminals"""

from warnings import warn
from enum import Enum

try:
    import colorama
    colorama.init()
    _COLORAMA_FOUND = True
except ImportError:
    _COLORAMA_FOUND = False


class _AnsiiColorBackend:
    def __init__(self):
        self._reset_key = "reset_all"
        self._setup_color_map()
        self._setup_style_map()

    def make_colored(self, text: str, color, style) -> str:
        if color is not None:
            text = self._color_map[str(color).lower()] + text
        if style is not None:
            text = self._style_map[str(style).lower()] + text
        if color is not None or style is not None:
            text = text + self._style_map[self._reset_key]
        return text

    def _setup_color_map(self) -> None:
        self._color_map: dict = {}
        for name in dir(colorama.Fore):
            if not name.startswith('_'):
                self._color_map[name.lower()] = getattr(colorama.Fore, name)

    def _setup_style_map(self) -> None:
        self._style_map: dict = {}
        for name in dir(colorama.Style):
            if not name.startswith('_'):
                self._style_map[name.lower()] = getattr(colorama.Style, name)
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
