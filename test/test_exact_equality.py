# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Test exact equality checks on values/arrays"""

from fieldcompare.predicates import ExactEquality, DefaultEquality
from fieldcompare._numpy_utils import make_array


def test_exact_equality_with_scalars():
    for check in [ExactEquality(), DefaultEquality()]:
        assert check(1, 1)
        assert check(1.0, 1.0)
        assert not check(2, 1)
        assert not check(2.0, 1.0)
        assert not check(1.0, 1.0 + 1e-4)


def test_exact_equality_with_lists():
    for check in [ExactEquality(), DefaultEquality()]:
        assert check([1, 2], [1, 2])
        assert check([1.0, 2.0], [1.0, 2.0])
        assert not check([1, 2], [1, 1])
        assert not check([1.0, 2.0], [1.0, 1.0])
        assert not check([1.0, 1.0], [1.0, 1.0 + 1e-4])


def test_exact_equality_with_arrays():
    for check in [ExactEquality(), DefaultEquality()]:
        assert check(make_array([1, 2]), make_array([1, 2]))
        assert check(make_array([1.0, 2.0]), make_array([1.0, 2.0]))
        assert not check(make_array([1, 2]), make_array([1, 1]))
        assert not check(make_array([1.0, 2.0]), make_array([1.0, 1.0]))
        assert not check(make_array([1.0, 1.0]), make_array([1.0, 1.0 + 1e-4]))


def test_vector_field_exact_equality():
    field1 = [[0, 0], [1, 2]]
    field2 = [[0, 0], [1, 2 + 1e-4]]

    for check in [ExactEquality(), DefaultEquality()]:
        assert check(field1, field1)
        assert check(field2, field2)

        assert not check(field1, field2)
        assert "2" in check(field1, field2).report.lower()


def test_exact_equality_mixed_types():
    list1 = [0, 1, 2, True, "hello"]
    list2 = [0, 1, 2, True, "hello"]
    list3 = [0, 1, 2, True, "hello22"]

    for check in [ExactEquality(), DefaultEquality()]:
        check = ExactEquality()
        assert check(list1, list2)
        assert check(make_array(list1), make_array(list2))
        assert not check(list1, list3)
        assert not check(make_array(list1), make_array(list3))
