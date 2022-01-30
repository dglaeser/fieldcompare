"""Common functions and types"""

import numpy as np


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
