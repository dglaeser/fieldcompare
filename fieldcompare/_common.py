"""Common functions and types"""

from typing import Iterable, Callable, TypeVar, Tuple
from time import time
from functools import wraps
import numpy as np

T = TypeVar("T")

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


def _is_iterable(thing) -> bool:
    return isinstance(thing, Iterable)


def _measure_time(action: Callable[..., T]) -> Callable[..., Tuple[float, T]]:
    @wraps(action)
    def _wrapper_measure_time(*args, **kwargs) -> Tuple[float, T]:
        before = time()
        result = action(*args, **kwargs)
        after = time()
        return (after - before), result
    return _wrapper_measure_time
