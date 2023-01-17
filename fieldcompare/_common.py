"""Common functions and types"""

from typing import Callable, TypeVar, Tuple
from time import time
from functools import wraps
from numpy import finfo

from ._numpy_utils import Array
from .protocols import DynamicTolerance


def _default_base_tolerance() -> DynamicTolerance:
    def _get_eps(arr: Array) -> float:
        try:
            return float(finfo(arr.dtype).eps)
        except ValueError:
            return float(finfo(float).eps)

    def _get(first: Array, second: Array) -> float:
        return min(_get_eps(first), _get_eps(second))

    return _get


T = TypeVar("T")


def _measure_time(action: Callable[..., T]) -> Callable[..., Tuple[float, T]]:
    @wraps(action)
    def _wrapper_measure_time(*args, **kwargs) -> Tuple[float, T]:
        before = time()
        result = action(*args, **kwargs)
        after = time()
        return (after - before), result

    return _wrapper_measure_time
