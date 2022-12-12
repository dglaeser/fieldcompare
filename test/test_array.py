"""Test some helper functions for arrays"""

from pytest import raises

from fieldcompare._array import (
    make_array,
    make_initialized_array,
    make_uninitialized_array,
    sub_array,
    flatten,
    accumulate,
    adjacent_difference,
    all_true,
    append_to_array,
    elements_less,
    get_sorting_index_map,
    get_lex_sorting_index_map,
    abs_array,
    max_element,
    min_element,
    max_column_elements,
    rel_diff,
    abs_diff,
    find_first_unequal,
    find_first_fuzzy_unequal
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


def test_abs_array():
    arr = make_array([-1, -2, -3])
    arr = abs_array(arr)
    assert _check_array_equal(arr, [1, 2, 3])


def test_min_element():
    arr = make_array([4, 6, 1])
    assert min_element(arr) == 1


def test_max_element():
    arr = make_array([4, 6, 1])
    assert max_element(arr) == 6


def test_max_column_elements():
    arr = make_array([
        make_array([4, 2, 8]),
        make_array([1, 2, 3]),
        make_array([10, 2, 14])
    ])
    arr = max_column_elements(arr)
    assert _check_array_equal(arr, [10, 2, 14])


def test_scalar_array_rel_diff():
    arr1 = make_array([1., 2., 3.])
    arr2 = make_array([2., 4., 6.])
    diff = rel_diff(arr1, arr2)
    assert all(
        abs(_diff - 1) < 1e-6 for _diff in diff
    )


def test_vector_array_rel_diff():
    arr1 = make_array([
        make_array([1., 2., 3.]),
        make_array([1., 2., 3.])
    ])
    arr2 = make_array([
        make_array([3., 6., 9.]),
        make_array([3., 6., 9.])
    ])
    diff = rel_diff(arr1, arr2)
    assert all(
        all(abs(_entry - 2) < 1e-6 for _entry in _diff)
        for _diff in diff
    )


def test_scalar_array_abs_diff():
    arr1 = make_array([0., 0., 0.])
    arr2 = make_array([2., 4., 6.])
    diff = abs_diff(arr1, arr2)
    assert all(
        abs(_diff - _v2) < 1e-6 for _diff, _v2 in zip(diff, arr2)
    )


def test_vector_array_abs_diff():
    arr1 = make_array([
        make_array([0., 0., 0.]),
        make_array([0., 0., 0.])
    ])
    arr2 = make_array([
        make_array([2., 4., 6.]),
        make_array([2., 4., 6.])
    ])
    diff = abs_diff(arr1, arr2)
    assert all(
        all(
            abs(_diff_entry - _arr2_entry) < 1e-6
            for _diff_entry, _arr2_entry in zip(_diff, _arr2)
        )
        for _diff, _arr2 in zip(diff, arr2)
    )


def test_find_first_unequal():
    arr1 = make_array([13, 7, 42, 8])
    arr2 = make_array([13, 7, 42, 9])
    assert find_first_unequal(arr1, arr2) == (8, 9)


def test_find_first_fuzzy_unequal():
    eps = 1e-12
    arr1 = make_array([13., 7., 42., 8.])
    arr2 = make_array([13.+eps, 7.-eps, 42.+eps, 9.])
    assert find_first_fuzzy_unequal(arr1, arr2) == (8., 9.)
