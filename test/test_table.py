from pytest import raises
from numpy import array

from fieldcompare.tabular import Table


def test_table_construction_from_number_of_rows():
    _ = Table(num_rows=3)


def test_table_construction_from_index_map():
    _ = Table(idx_map=array([3, 1, 2]))


def test_table_construction_from_float_array_raises_value_error():
    with raises(ValueError):
        _ = Table(idx_map=array([3., 1., 2.]))


def test_table_construction_from_2d_array_raises_value_error():
    with raises(ValueError):
        _ = Table(idx_map=array([[3], [1], [2]]))


def test_table_construction_from_non_matching_index_map_raises_value_error():
    with raises(ValueError):
        _ = Table(num_rows=2, idx_map=array([3., 1., 2.]))


def test_table_construction_without_args_raises_value_error():
    with raises(ValueError):
        _ = Table()
