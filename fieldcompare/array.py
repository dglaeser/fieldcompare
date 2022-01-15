"""Arrays representing field values"""

from multiprocessing.sharedctypes import Value
from typing import Iterable, Sequence, Tuple

from numpy import ndarray as Array
from numpy import array as _array
from numpy import array_equal as _array_equal
from numpy import equal as _equal
from numpy import all as _all_true

def is_array(input_array) -> bool:
    return isinstance(input_array, Array)

def make_array(input_array: Iterable) -> Array:
    return _array(input_array)

def sub_array(input_array: Iterable, start: int, end: int) -> Array:
    if isinstance(input_array, Array):
        return input_array[start:end]
    if isinstance(input_array, Sequence):
        return make_array(input_array[start:end])
    return make_array(input_array)[start:end]

def array_equal(first: Array, second: Array) -> bool:
    return _array_equal(first, second)

def get_first_non_equal(first: Array, second: Array) -> Tuple:
    bitset = _equal(first, second)
    for idx, is_equal in enumerate(bitset):
        if not _all_true(is_equal):
            return first[idx], second[idx]
    raise ValueError("Input arrays contain no non-equal values.")
