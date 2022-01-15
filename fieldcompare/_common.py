"""Commonly used classes and functions"""

from typing import Iterable

import numpy
from numpy import ndarray as Array

numpy.set_printoptions(floatmode="unique")

def make_array(input_array: Iterable) -> Array:
    return numpy.array(input_array)

def eq_bitset_exact(first: Array, second: Array) -> Array:
    return numpy.equal(first, second)

def eq_exact(first: Array, second: Array) -> bool:
    return numpy.array_equal(first, second)

def first_false_index(input_array: Array) -> int:
    for idx, entry in enumerate(input_array):
        if not numpy.all(entry):
            return idx
    raise ValueError("All entries evaluate to True")
