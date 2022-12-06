"""Array representing field values and associated helper functions"""

from typing import Iterable, Sequence, Tuple, Optional, Union, SupportsIndex

import numpy as np
from numpy import ndarray as Array
from numpy.typing import ArrayLike

from fieldcompare._common import _default_base_tolerance


def make_uninitialized_array(size: int, dtype=None) -> Array:
    return Array(shape=(size,), dtype=dtype)


def make_initialized_array(size: int, init_value, dtype=None) -> Array:
    result: Array = Array(shape=(size,), dtype=dtype)
    result.fill(init_value)
    return result


def make_array(input_array: ArrayLike, dtype=None) -> Array:
    """Make an array from the given sequence"""
    return np.array(input_array, dtype=dtype)


def as_array(input_array: Union[Array, ArrayLike]) -> Array:
    """Return an array with the values of the given input sequence"""
    if isinstance(input_array, Array):
        return input_array
    return np.array(input_array)


def sub_array(input_array: Array, start: int, end: int) -> Array:
    """Return the subset of the given array in the range [start, end)"""
    if isinstance(input_array, Array):
        return input_array[start:end]
    if isinstance(input_array, Sequence):
        return make_array(input_array[start:end])
    raise ValueError("Provided type is neither array nor sequence")


def has_floats(input_array: Array) -> bool:
    """Return true if the array contains at least one floating-point value"""
    def _has_floats(value) -> bool:
        if isinstance(value, Array) and value.dtype.name != "object":
            return "float" in input_array.dtype.name
        if np.isscalar(value):
            return isinstance(value, np.floating) or isinstance(value, float)
        elif isinstance(value, Iterable):
            return any(_has_floats(v) for v in value)
        raise ValueError("Could not determine if array has floats")
    return _has_floats(input_array)


def as_string(input: ArrayLike) -> str:
    """Return the string representation of the given array-like value"""
    with np.printoptions(floatmode="unique"):
        return np.array2string(as_array(input))


def flatten(input_array) -> Array:
    """Return the input array as flat array"""
    return input_array.flatten()


def accumulate(input_array: Array, axis: SupportsIndex = 0) -> Array:
    return np.sum(input_array, axis=axis)


def adjacent_difference(input_array: Array, axis: int = -1) -> Array:
    return np.diff(input_array, axis=axis)


def all_true(input_array: Array, axis: Optional[SupportsIndex] = None):
    """Check whether all entries of a boolean array are true along the given axis."""
    return np.all(input_array, axis=axis)


def any_true(input_array: Array, axis: Optional[SupportsIndex] = None):
    """Check whether any entry of a boolean array is true along the given axis."""
    return np.any(input_array, axis=axis)


def append_to_array(input_array: Array, values) -> Array:
    """Append the given value(s) to the given array and return the result."""
    return np.append(input_array, values)


def elements_less(first: Array, second: Array) -> Array:
    """Return a boolean array indicating entries of first that smaller than those of second."""
    return np.less(first, second)


def get_lex_sorting_index_map(input_array: Array) -> Array:
    """Get the list of indices for sorting the array lexicographically. Expects multi-dimensional arrays."""
    dimension = len(input_array[0])
    return np.lexsort(
        tuple(input_array[:, i] for i in reversed(range(dimension)))
    )


def get_sorting_index_map(input_array: Array) -> Array:
    """Get the list of indices that would sort the array."""
    return np.argsort(input_array)


def abs_array(input_array: Array) -> Array:
    """Return a copy of the array with the absolute values of the given array."""
    return np.fabs(input_array)


def min_element(input_array: Array):
    """Return the minimum value within the array. Expects arrays of scalars."""
    return input_array[np.argmin(input_array)]


def max_element(input_array: Array):
    """Return the maximum value within the array. Expects arrays of scalars."""
    return input_array[np.argmax(input_array)]


def max_column_elements(input_array: Array):
    """Return the maximum values of the array columns. For scalar arrays, returns max_element()."""
    if len(input_array) == 0:
        return None
    if np.isscalar(input_array[0]):
        return max_element(input_array)
    return make_array([
        max_element(input_array[:, i])
        for i in range(len(input_array[0]))
    ])


def rel_diff(first: Array, second: Array) -> Array:
    """Return the relative difference (w.r.t first array) between the two given arrays."""
    zeros = np.equal(first, 0.0)
    non_computables = np.logical_or(zeros, np.logical_not(np.isfinite(first)))
    computables = np.logical_not(non_computables)
    rdiff = make_array(first)
    rdiff[computables] = np.abs(second[computables] - first[computables])/first[computables]
    rdiff[non_computables] = np.nan
    rdiff[zeros] = np.inf
    return rdiff


def abs_diff(first: Array, second: Array) -> Array:
    """Return the absolute difference between the two given arrays."""
    return np.abs(second - first)


def find_first_unequal(first: Array, second: Array) -> Optional[Tuple]:
    """Search for the first unequal pair of values in the given array."""
    try:
        # this only works for single-type arrays (but is fast)
        bitset = np.equal(first, second)
        if not np.all(bitset):
            return _get_first_false_pair(bitset, first, second)
    except Exception:
        # handle case of scalars
        if not first.shape and not second.shape:
            if not np.array_equal(first, second):
                return (first, second)

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
            # handle case of scalars
            if not first.shape and not second.shape:
                if not np.allclose(first, second, rtol=rel_tol, atol=abs_tol):
                    return (first, second)

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
