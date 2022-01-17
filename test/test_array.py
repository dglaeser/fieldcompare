"""Test some helper functions for arrays"""

from pytest import raises

from context import fieldcompare
from fieldcompare import make_array, sub_array
from fieldcompare.array import make_initialized_array, make_uninitialized_array

def test_array_factory_functions():
    arr1 = make_array([0, 1, 2])
    arr2 = make_array(arr1)
    arr3 = make_array((0, 1, 2))
    assert arr1[0] == arr2[0]
    assert arr2[0] == arr3[0]

    arr1[0] = 1
    assert arr1[0] != arr2[0]
    assert arr1[0] != arr3[0]

def test_sub_array_extraction():
    arr1 = sub_array([0, 1, 2], 0, 1)
    assert arr1[0] == 0 and len(arr1) == 1

    with raises(ValueError):
        sub_array({1: False, 2: False}, 0, 1)
    with raises(ValueError):
        sub_array((i for i in range(3)), 0, 1)

def test_fixed_size_array_construction():
    arr1 = make_initialized_array(size=10, init_value=1.0)
    assert all(v == 1.0 for v in arr1)
    arr1 = make_uninitialized_array(size=10, dtype="object")
    assert all(v is None for v in arr1)

if __name__ == "__main__":
    test_array_factory_functions()
    test_sub_array_extraction()
    test_fixed_size_array_construction()
