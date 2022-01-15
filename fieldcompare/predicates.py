"""Classes and functions related to predicates"""

from typing import Iterable, Callable
from fieldcompare._common import _get_as_string
from fieldcompare.array import Array, sub_array, is_array, make_array
from fieldcompare.array import array_equal, get_first_non_equal
from fieldcompare.field import Field, FieldInterface


class PredicateResult:
    """Stores the result of a predicate evaluation"""
    def __init__(self, value: bool, report: str = "") -> None:
        self._value = value
        self._report = report

    def __bool__(self) -> bool:
        return self._value

    @property
    def report(self) -> str:
        return self._report

    @property
    def value(self) -> bool:
        return self._value


ArrayPredicate = Callable[[Array, Array], PredicateResult]

class ExactArrayEquality:
    """Compares two arrays for exact equality"""
    def __call__(self, first: Array, second: Array) -> PredicateResult:
        if not is_array(first): first = make_array(first)
        if not is_array(second): second = make_array(second)
        if not array_equal(first, second):
            val1, val2 = get_first_non_equal(first, second)
            return PredicateResult(False, _get_equality_fail_message(val1, val2))
        return PredicateResult(True)


class FieldPredicate:
    """Evaluates a predicate on two fields"""
    def __init__(self,
                 array_predicate: ArrayPredicate,
                 ignore_names_mismatch: bool = False,
                 ignore_length_mismatch: bool = False) -> None:
        self._array_predicate = array_predicate
        self._ignore_names_mismatch = ignore_names_mismatch
        self._ignore_length_mismatch = ignore_length_mismatch

    def __call__(self, first: FieldInterface, second: FieldInterface) -> PredicateResult:
        if not self._ignore_names_mismatch and first.name != second.name:
            return PredicateResult(False, "Names do not match")
        if len(first.values) == len(second.values):
            return self._array_predicate(first.values, second.values)
        if not self._ignore_length_mismatch:
            return PredicateResult(False, "Lengths do not match")
        min_len = min(len(first.values), len(second.values))
        return self._array_predicate(
            sub_array(first.values, 0, min_len),
            sub_array(second.values, 0, min_len)
        )


class ExactFieldEquality(FieldPredicate):
    """Compare two fields for exact equality"""
    def __init__(self, *args, **kwargs) -> None:
        FieldPredicate.__init__(self, ExactArrayEquality(), *args, **kwargs)


def _get_equality_fail_message(val1, val2) -> str:
    return "{} and {} have compared unequal".format(
        _get_as_string(val1),
        _get_as_string(val2)
    )
