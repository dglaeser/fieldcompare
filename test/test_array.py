"""Test some helper functions for arrays"""

from pytest import raises

from fieldcompare import make_array, sub_array
from fieldcompare import make_initialized_array, make_uninitialized_array
from fieldcompare._array import (
    is_array,
    flatten,
    accumulate,
    adjacent_difference,
    all_true,
    append_to_array,
    elements_less,
    get_sorting_index_map,
    get_lex_sorting_index_map
)


def _check_array_equal(arr1, arr2) -> bool:
    if len(arr1) != len(arr2):
        return False
    return all(a == b for a, b in zip(arr1, arr2))


def test_make_uninitialized_array():
    array = make_uninitialized_array(size=10, dtype="object")
    assert len(array) == 10
    assert all(v is None for v in array)


def test_make_initialized_array():
    array = make_initialized_array(size=10, dtype=int, init_value=13)
    assert len(array) == 10
    assert all(v == 13 for v in array)


def test_make_array_from_list():
    arr = make_array([0, 1, 2])
    assert _check_array_equal(arr, [0, 1, 2])


def test_make_array_from_array():
    arr = make_array([0, 1, 2])
    arr_cpy = make_array(arr)
    assert _check_array_equal(arr_cpy, arr)


def test_make_array_from_tuple():
    arr = make_array((0, 1, 2))
    assert _check_array_equal(arr, [0, 1, 2])


def test_make_array_yields_copy():
    arr = make_array([0, 1, 2])
    arr_cpy = make_array(arr)
    arr_cpy[0] = 13
    assert _check_array_equal(arr, [0, 1, 2])
    assert _check_array_equal(arr_cpy, [13, 1, 2])


def test_sub_array_extraction():
    arr1 = sub_array(make_array([0, 1, 2]), 0, 1)
    assert arr1[0] == 0 and len(arr1) == 1

    with raises(ValueError):
        sub_array({1: False, 2: False}, 0, 1)
    with raises(ValueError):
        sub_array((i for i in range(3)), 0, 1)


def test_is_array():
    assert not is_array([1, 2, 3])
    assert is_array(make_array([1, 2, 3]))


def test_flaten_array():
    arr = make_array([[0, 1], [2, 3]])
    assert _check_array_equal(flatten(arr), [0, 1, 2, 3])


def test_array_accumulate():
    assert accumulate(make_array([1, 2, 3])) == 6


def test_array_adjacent_difference():
    adj_diff = adjacent_difference(make_array([1, 2, 4]))
    assert len(adj_diff) == 2
    assert _check_array_equal(adj_diff, [1, 2])


def test_array_all_true():
    bool_arr = make_array([True, False, True])
    assert not all_true(bool_arr)
    bool_arr[1] = True
    assert all_true(bool_arr)


def test_append_to_array():
    arr = make_array([1, 2, 3])
    arr = append_to_array(arr, 43)
    assert _check_array_equal(arr, [1, 2, 3, 43])


def test_array_elements_less():
    arr1 = make_array([1, 2, 3])
    arr2 = make_array([2, 3, 4])
    less = elements_less(arr1, arr2)
    assert _check_array_equal(less, [True, True, True])

    arr2[1] = 0
    less = elements_less(arr1, arr2)
    assert _check_array_equal(less, [True, False, True])


def test_sort_array():
    arr = make_array([3, 2, 6])
    arr = get_sorting_index_map(arr)
    assert _check_array_equal(arr, [1, 0, 2])


def test_lex_sort_array_columns():
    arr = make_array([
        make_array([2, 1]),
        make_array([1, 4]),
        make_array([2, 0])
    ])
    arr = get_lex_sorting_index_map(arr)
    assert _check_array_equal(arr, [1, 2, 0])
