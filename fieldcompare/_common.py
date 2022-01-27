"""Common functions and types"""

from warnings import warn
from enum import Enum
import numpy as np

try:
    import colorama
    colorama.init()
    _COLORAMA_FOUND = True
except ImportError:
    _COLORAMA_FOUND = False


class _AnsiiColorBackend:
    def __init__(self):
        self._color_map: dict = {}
        self._style_map: dict = {}
        self._use_colors = _COLORAMA_FOUND
        self._reset_key = "reset_all"
        if self._use_colors:
            self._setup_color_map()
            self._setup_style_map()

    def style_string(self, text: str, color, style) -> str:
        if not self._use_colors:
            return text

        if color is not None:
            text = self._color_map[str(color).lower()] + text
        if style is not None:
            text = self._style_map[str(style).lower()] + text
        if color is not None or style is not None:
            text = text + self._style_map[self._reset_key]
        return text

    def activate_colors(self) -> None:
        if _COLORAMA_FOUND:
            self._use_colors = True
        else:
            warn(RuntimeWarning(
                "Cannot activate color output: Colorama not found"
            ))

    def deactivate_colors(self) -> None:
        self._use_colors = False

    def _setup_color_map(self) -> None:
        for name in dir(colorama.Fore):
            if not name.startswith('_'):
                self._color_map[name.lower()] = getattr(colorama.Fore, name)

    def _setup_style_map(self) -> None:
        for name in dir(colorama.Style):
            if not name.startswith('_'):
                self._style_map[name.lower()] = getattr(colorama.Style, name)
        assert self._reset_key in self._style_map


_COLOR_BACKEND = _AnsiiColorBackend()

def deactivate_colored_output() -> None:
    _COLOR_BACKEND.deactivate_colors()

def activate_colored_output() -> None:
    _COLOR_BACKEND.activate_colors()


class TextColor(Enum):
    red = "red"
    green = "green"
    blue = "blue"
    magenta = "magenta"

    def __str__(self) -> str:
        return str(self.value)

class TextStyle(Enum):
    dim = "DIM"
    normal = "NORMAL"
    bright = "BRIGHT"

    def __str__(self) -> str:
        return str(self.value)

def _style_text(text: str,
                color: TextColor = None,
                style: TextStyle = None) -> str:
    return _COLOR_BACKEND.style_string(text, color, style)


def _is_scalar(obj) -> bool:
    return np.isscalar(obj)


def _get_as_string(obj) -> str:
    if isinstance(obj, (np.floating, float)):
        return np.format_float_scientific(obj, unique=True)
    if isinstance(obj, np.ndarray):
        with np.printoptions(floatmode="unique"):
            return np.array2string(obj)
    return str(obj)


def _default_base_tolerance() -> float:
    return 1e-9
