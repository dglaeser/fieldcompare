"""Arrays representing field values"""

from typing import Iterable, Sequence, Tuple, Optional

import numpy as np
from numpy import ndarray as Array

from fieldcompare._common import _default_base_tolerance


def make_uninitialized_array(size: int, dtype) -> Array:
    return Array(shape=(size,), dtype=dtype)


def make_initialized_array(size: int, dtype, init_value) -> Array:
    result: Array = Array(shape=(size,), dtype=dtype)
    result.fill(init_value)
    return result


def make_array(input_array: Iterable) -> Array:
    """Make an array from the given iterable"""
    return np.array(input_array)


def accumulate(input_array: Array, axis = None) -> Array:
    return np.sum(input_array, axis=axis)


def adjacent_difference(input_array: Array, axis: int = -1) -> Array:
    return np.diff(input_array, axis=axis)


def sub_array(input_array: Iterable, start: int, end: int) -> Array:
    """Return the subset of the given array in the range [start, end)"""
    if isinstance(input_array, Array):
        return input_array[start:end]
    if isinstance(input_array, Sequence):
        return make_array(input_array[start:end])
    return make_array(input_array)[start:end]


def is_array(input_array) -> bool:
    """Return true if the given object is an Array"""
    return isinstance(input_array, Array)


def lex_sort_array_columns(input_array: Array) -> Array:
    """Sort an array lexicographically. This expects multi-dimensional arrays."""
    dimension = len(input_array[0])
    return np.lexsort(
        tuple(input_array[:, i] for i in reversed(range(dimension)))
    )


def min_element(input_array: Array):
    """Return the minimum value within the array. Expects arrays of scalars."""
    return input_array[np.argmin(input_array)]


def max_element(input_array: Array):
    """Return the maximum value within the array. Expects arrays of scalars."""
    return input_array[np.argmax(input_array)]


def find_first_unequal(first: Array, second: Array) -> Optional[Tuple]:
    """Search for the first unequal pair of values in the given array."""
    try:
        # this only works for single-type arrays (but is fast)
        bitset = np.equal(first, second)
        if not np.all(bitset):
            return _get_first_false_pair(bitset, first, second)
    except Exception:
        # this works also for mixed-type arrays (slower)
        for val1, val2 in zip(first, second):
            if not np.array_equal(val1, val2):
                return (val1, val2)
    return None


def find_first_fuzzy_unequal(first: Array,
                             second: Array,
                             rel_tol: float = _default_base_tolerance(),
                             abs_tol: float = _default_base_tolerance()) -> Optional[Tuple]:
    """Search for the first fuzzy-unequal pair of values in the given array."""
    try:
        # this works if all entries have the same shape store fuzzy-comparable types
        bitset = np.isclose(first, second, rtol=rel_tol, atol=abs_tol)
        if not np.all(bitset):
            return _get_first_false_pair(bitset, first, second)
    except Exception:
        try:
            # this works also for entries with different shapes but fuzzy-comparable types
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
