"""Common functions and types"""

from typing import Callable, TypeVar, Tuple
from time import time
from functools import wraps
from numpy import finfo, find_common_type, issubdtype, floating, integer

from ._numpy_utils import Array
from .protocols import DynamicTolerance


def _default_base_tolerance() -> DynamicTolerance:
    def _get(first: Array, second: Array) -> float:
        common_type = find_common_type(array_types=[first.dtype, second.dtype], scalar_types=[])
        # Integers should be exactly equal
        if issubdtype(common_type, integer):
            return 0.0
        assert issubdtype(common_type, floating)
        return float(finfo(common_type).eps)

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
