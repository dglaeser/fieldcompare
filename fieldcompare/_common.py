"""Common functions and types"""

from enum import Enum
import numpy as np
import colorama
colorama.init()

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


class TextColor(Enum):
    red = colorama.Fore.RED,
    green = colorama.Fore.GREEN,
    blue = colorama.Fore.BLUE,

class TextStyle(Enum):
    dim = colorama.Style.DIM,
    normal = colorama.Style.NORMAL,
    bright = colorama.Style.BRIGHT,

def _style_text(text: str, color: TextColor = None, style: TextStyle = None) -> str:
    text = color.value[0] + text if color is not None else text
    text = style.value[0] + text if style is not None else text
    if any(v is not None for v in [color, style]):
        text = text + colorama.Style.RESET_ALL
    return text
