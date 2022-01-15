"""Arrays representing field values"""

from typing import Iterable, Sequence, Tuple, Optional

import numpy as np
from numpy import ndarray as Array

from fieldcompare._common import _default_base_tolerance


def is_array(input_array) -> bool:
    return isinstance(input_array, Array)


def make_array(input_array: Iterable) -> Array:
    return np.array(input_array)


def lex_sort(input_array: Array) -> Array:
    dimension = len(input_array[0])
    return np.lexsort(
        tuple(input_array[:,i] for i in reversed(range(dimension)))
    )


def sub_array(input_array: Iterable, start: int, end: int) -> Array:
    if isinstance(input_array, Array):
        return input_array[start:end]
    if isinstance(input_array, Sequence):
        return make_array(input_array[start:end])
    return make_array(input_array)[start:end]


def find_first_unequal(first: Array, second: Array) -> Optional[Tuple]:
    try:
        bitset = np.equal(first, second)
        if not np.all(bitset):
            return _get_first_false_pair(bitset, first, second)
    except Exception:
        for val1, val2 in zip(first, second):
            if not np.array_equal(val1, val2):
                return (val1, val2)
    return None


def find_first_fuzzy_unequal(first: Array,
                             second: Array,
                             rel_tol: float = _default_base_tolerance(),
                             abs_tol: float = _default_base_tolerance()) -> Optional[Tuple]:
    try:
        bitset = np.isclose(first, second, rtol=rel_tol, atol=abs_tol)
        if not np.all(bitset):
            return _get_first_false_pair(bitset, first, second)
    except Exception:
        try:
            for val1, val2 in zip(first, second):
                if not np.allclose(val1, val2, rtol=rel_tol, atol=abs_tol):
                    return (val1, val2)
        except Exception:
            raise ValueError("Could not fuzzy-compare the given arrays.")
    return None


def _get_first_false_pair(bool_array: Array, first: Array, second: Array) -> Tuple:
    for idx, predicate_result in enumerate(bool_array):
        if not np.all(predicate_result):
            return first[idx], second[idx]
    raise ValueError("Boolean array contains no False entry.")
