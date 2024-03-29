# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Common functions and types"""

from __future__ import annotations
from typing import Callable, TypeVar
from time import time
from functools import wraps
from numpy import finfo, promote_types, issubdtype, floating, integer

from ._numpy_utils import Array
from .protocols import DynamicTolerance


def _default_base_tolerance() -> DynamicTolerance:
    def _get(first: Array, second: Array) -> float:
        common_type = promote_types(first.dtype, second.dtype)
        # For integers, we use exact comparison as a default
        if issubdtype(common_type, integer):
            return 0.0
        # For complicated structured types, we raise an exception and ask for a manual threshold
        if not issubdtype(common_type, floating):
            raise ValueError(
                "Could not deduce a default tolerance"
                f" for array types {first.dtype} and {second.dtype}."
                " Please manually provide a tolerance."
            )
        return float(finfo(common_type).eps)

    return _get


T = TypeVar("T")


def _measure_time(action: Callable[..., T]) -> Callable[..., tuple[float, T]]:
    @wraps(action)
    def _wrapper_measure_time(*args, **kwargs) -> tuple[float, T]:
        before = time()
        result = action(*args, **kwargs)
        after = time()
        return (after - before), result

    return _wrapper_measure_time
