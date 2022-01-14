"""Commonly used classes and functions"""

from typing import Iterable

import numpy
from numpy import ndarray as Array

def make_array(input_array: Iterable) -> Array:
    return numpy.array(input_array)

def check_arrays_equal(first: Array, second: Array) -> Array:
    return numpy.equal(first, second)
