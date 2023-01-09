"""Array representing field values and associated helper functions"""

from typing import Iterable, Sequence, Tuple, Optional, Union, SupportsIndex

import numpy as np
from numpy import ndarray
from numpy.typing import ArrayLike as np_arraylike


Array = ndarray
ArrayLike = np_arraylike


def make_uninitialized_array(size: int, dtype=None) -> Array:
    return Array(shape=(size,), dtype=dtype)


def make_initialized_array(size: int, init_value, dtype=None) -> Array:
    result: Array = Array(shape=(size,), dtype=dtype)
    result.fill(init_value)
    return result


def make_zeros(shape: Tuple[int, ...], dtype=None) -> Array:
    return np.zeros(shape, dtype)


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


def concatenate(arrays: Sequence[Array]) -> Array:
    return np.concatenate(arrays)


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


def is_index_array(input_array: Array) -> bool:
    """Return true if the array consists of integer values"""
    if len(input_array.shape) > 1:
        return False
    return input_array.dtype in [np.int8, np.int16, np.int32, np.int64]


def as_string(input: ArrayLike, digits: Optional[int] = None) -> str:
    """Return the string representation of the given array-like value"""
    if digits is not None:
        with np.printoptions(floatmode="fixed", precision=digits):
            return np.array2string(as_array(input))
    with np.printoptions(floatmode="unique"):
        return np.array2string(as_array(input))


def flatten(input_array) -> Array:
    """Return the input array as flat array"""
    return input_array.flatten()


def accumulate(input_array: Array, axis: SupportsIndex = 0) -> Array:
    return np.sum(input_array, axis=axis)


def get_adjacent_fuzzy_equal_indices(values: Array, abs_tol: float, rel_tol: float) -> Array:
    result = np.isclose(values[:-1], values[1:], atol=abs_tol, rtol=rel_tol)
    return append_to_array(result, False)


def any_true(input_array: Array, axis: Optional[SupportsIndex] = None):
    """Check whether any entry of a boolean array is true along the given axis."""
    return np.any(input_array, axis=axis)


def append_to_array(input_array: Array, values) -> Array:
    """Append the given value(s) to the given array and return the result."""
    return np.append(input_array, values)


def get_lex_sorting_index_map(input_array: Array) -> Array:
    """Get the list of indices for sorting the array lexicographically. Expects multi-dimensional arrays."""
    dimension = len(input_array[0])
    return np.lexsort(tuple(input_array[:, i] for i in reversed(range(dimension))))


def get_fuzzy_lex_sorting_index_map(input_array: Array, abs_tol: float, rel_tol: float) -> Array:
    """Get the list of indices for fuzzy-sorting the array lexicographically. Expects 2d arrays."""
    if len(input_array.shape) != 2:
        raise ValueError("Implementation only works for 2d arrays")
    idx_map = np.argsort(input_array[:, 0])
    sorted = input_array[idx_map]
    for dim in range(1, input_array.shape[1]):
        equals = get_adjacent_fuzzy_equal_indices(sorted[:, dim - 1], abs_tol=abs_tol, rel_tol=rel_tol)
        for start, end in walk_adjacent_true_index_ranges(equals):
            indices = np.argsort(sorted[start:end][:, dim])
            idx_map[start:end] = idx_map[start:end][indices]
            sorted[start:end] = input_array[idx_map[start:end]]
    return idx_map


def walk_adjacent_true_index_ranges(bool_array: Array, include_upper_edge: bool = True) -> Iterable[Tuple[int, int]]:
    """Get an iterable over index chunks for which the given boolean array is true"""
    begin, end, in_true_block = 0, 0, False
    for i in range(len(bool_array)):
        if bool_array[i] and not in_true_block:
            begin, in_true_block = i, True
        elif not bool_array[i] and in_true_block:
            end, in_true_block = i, False
            yield (begin, end + 1 if include_upper_edge else end)


def get_sorting_index_map(input_array: Array) -> Array:
    """Get the list of indices that would sort the array."""
    return np.argsort(input_array)


def max_element(input_array: Array):
    """Return the maximum value within the array. Expects arrays of scalars."""
    return input_array[np.argmax(input_array)]


def max_value(input_array: Array) -> float:
    """Return the maximum ocurring scalar value in the array."""
    return float(np.max(input_array))


def max_abs_value(input_array: Array) -> float:
    """Return the maximum absolute scalar value occurring in the given array."""
    return max_value(abs_array(input_array))


def max_column_elements(input_array: Array):
    """Return the maximum values of the array columns. For scalar arrays, returns max_element()."""
    if len(input_array) == 0:
        return None
    if np.isscalar(input_array[0]):
        return max_element(input_array)
    return make_array([max_element(input_array[:, i]) for i in range(len(input_array[0]))])


def rel_diff(first: Array, second: Array) -> Array:
    """Return the relative difference (w.r.t first array) between the two given arrays."""
    zeros = np.equal(first, 0.0)
    non_computables = np.logical_or(zeros, np.logical_not(np.isfinite(first)))
    computables = np.logical_not(non_computables)
    rdiff = make_array(first)
    rdiff[computables] = np.abs(second[computables] - first[computables]) / first[computables]
    rdiff[non_computables] = np.nan
    rdiff[zeros] = np.inf
    return rdiff


def abs_array(input_array: Array) -> Array:
    """Return an array containing the absolute values of the given array"""
    return np.abs(input_array)


def abs_diff(first: Array, second: Array) -> Array:
    """Return the absolute difference between the two given arrays."""
    return abs_array(second - first)


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


def fuzzy_equal(first: Array, second: Array, rel_tol: float, abs_tol: float) -> Array:
    """
    Return the indices at which the two arrays are fuzzy_equal.
    The arrays are considered fuzzy equal if for each scalar value the following relation holds:
    `abs(a - b) <= max(rel_tol*max(a, b), abs_tol)`
    """
    abs_diff = np.abs(second - first)
    thresholds = np.maximum(np.abs(first), np.abs(second))
    thresholds *= rel_tol
    thresholds = np.maximum(thresholds, abs_tol)
    return np.less_equal(abs_diff, thresholds)


def find_first_fuzzy_unequal(first: Array, second: Array, rel_tol: float, abs_tol: float) -> Optional[Tuple]:
    """Search for the first fuzzy-unequal pair of values in the given array."""
    try:
        # this works if all entries have the same shape store fuzzy-comparable types
        bitset = fuzzy_equal(first, second, rel_tol=rel_tol, abs_tol=abs_tol)
        if not np.all(bitset):
            return _get_first_false_pair(bitset, first, second)
    except Exception:
        try:
            # handle case of scalars
            if not first.shape and not second.shape:
                return (
                    (first, second) if not fuzzy_equal(first, second, rel_tol=rel_tol, abs_tol=abs_tol).all() else None
                )

            # this works also for entries with different shapes but fuzzy-comparable types
            for val1, val2 in zip(first, second):
                if not fuzzy_equal(as_array(val1), as_array(val2), rel_tol=rel_tol, abs_tol=abs_tol).all():
                    return (val1, val2)
        except Exception:
            raise ValueError("Could not fuzzy-compare the given arrays.")
    return None


def _get_first_false_pair(bool_array: Array, first: Array, second: Array) -> Tuple:
    for idx, predicate_result in enumerate(bool_array):
        if not np.all(predicate_result):
            return first[idx], second[idx]
    raise ValueError("Boolean array contains no False entry.")
