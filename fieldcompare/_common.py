"""Common functions and types"""

from typing import Callable, TypeVar, Tuple
from time import time
from functools import wraps


def _default_base_tolerance() -> float:
    return 1e-9


T = TypeVar("T")
def _measure_time(action: Callable[..., T]) -> Callable[..., Tuple[float, T]]:
    @wraps(action)
    def _wrapper_measure_time(*args, **kwargs) -> Tuple[float, T]:
        before = time()
        result = action(*args, **kwargs)
        after = time()
        return (after - before), result
    return _wrapper_measure_time
