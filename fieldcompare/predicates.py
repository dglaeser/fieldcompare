"""Classes and functions related to predicates on fields & arrays"""

from typing import Callable

from ._common import _get_as_string
from ._common import _default_base_tolerance

from .array import Array, sub_array, is_array, make_array
from .array import find_first_unequal
from .array import find_first_fuzzy_unequal
from .field import FieldInterface


class PredicateResult:
    """Stores the result of a predicate evaluation"""
    def __init__(self, value: bool, report: str = "") -> None:
        self._value = value
        self._report = report

    def __bool__(self) -> bool:
        return self._value

    @property
    def report(self) -> str:
        """Return a report of the predicate evaluation."""
        return self._report

    @property
    def value(self) -> bool:
        """Return the underlying boolean value"""
        return self._value


class ExactArrayEquality:
    """Compares two arrays for exact equality"""
    def __call__(self, first: Array, second: Array) -> PredicateResult:
        first = make_array(first) if not is_array(first) else first
        second = make_array(second) if not is_array(second) else second
        unequals = find_first_unequal(first, second)
        if unequals is not None:
            val1, val2 = unequals
            return PredicateResult(False, _get_equality_fail_message(val1, val2))
        return PredicateResult(True)


class FuzzyArrayEquality:
    """Compares two arrays for fuzzy equality"""
    def __init__(self,
                 rel_tol: float = _default_base_tolerance(),
                 abs_tol: float = _default_base_tolerance()) -> None:
        self._rel_tol = rel_tol
        self._abs_tol = abs_tol

    @property
    def relative_tolerance(self) -> float:
        """Return the relative tolerance used for fuzzy comparisons."""
        return self._rel_tol

    @relative_tolerance.setter
    def relative_tolerance(self, value: float) -> None:
        """Set the relative tolerance to be used for fuzzy comparisons."""
        self._rel_tol = value

    @property
    def absolute_tolerance(self) -> float:
        """Return the absolute tolerance used for fuzzy comparisons."""
        return self._rel_tol

    @absolute_tolerance.setter
    def absolute_tolerance(self, value: float) -> None:
        """Set the absolute tolerance to be used for fuzzy comparisons."""
        self._abs_tol = value

    def __call__(self, first: Array, second: Array) -> PredicateResult:
        if not is_array(first): first = make_array(first)
        if not is_array(second): second = make_array(second)
        unequals = find_first_fuzzy_unequal(first, second, self._rel_tol, self._abs_tol)
        if unequals is not None:
            val1, val2 = unequals
            return PredicateResult(
                False,
                _get_equality_fail_message(val1, val2)
                + f"\nUsed tolerances: relative={self._rel_tol}, absolute={self._abs_tol}"
            )
        return PredicateResult(True)


class DefaultArrayEquality(FuzzyArrayEquality):
    """Default choice of array equality checks. Checks fuzzy or exact depending on data type."""
    def __init__(self, *args, **kwargs) -> None:
        FuzzyArrayEquality.__init__(self, *args, **kwargs)

    def __call__(self, first: Array, second: Array) -> PredicateResult:
        def _is_float(arr: Array) -> bool:
            return "float" in arr.dtype.name
        if _is_float(first) and _is_float(second):
            return FuzzyArrayEquality.__call__(self, first, second)
        return ExactArrayEquality()(first, second)


ArrayPredicate = Callable[[Array, Array], PredicateResult]

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


class FuzzyFieldEquality(FieldPredicate):
    """Compare two fields for fuzzy equality"""
    def __init__(self, *args, **kwargs) -> None:
        FieldPredicate.__init__(self, FuzzyArrayEquality(), *args, **kwargs)

    def set_relative_tolerance(self, rel_tol: float) -> None:
        """Set the relative tolerance to be used for fuzzy comparisons."""
        self._array_predicate.relative_tolerance = rel_tol

    def set_absolute_tolerance(self, abs_tol: float) -> None:
        """Set the absolute tolerance to be used for fuzzy comparisons."""
        self._array_predicate.absolute_tolerance = abs_tol


class DefaultFieldEquality(FieldPredicate):
    """Default implementation for field equality. Checks fuzzy or exact depending on data type."""
    def __init__(self, *args, **kwargs) -> None:
        FieldPredicate.__init__(self, DefaultArrayEquality(), *args, **kwargs)

    def set_relative_tolerance(self, rel_tol: float) -> None:
        """Set the relative tolerance to be used for fuzzy comparisons."""
        self._array_predicate.relative_tolerance = rel_tol

    def set_absolute_tolerance(self, abs_tol: float) -> None:
        """Set the absolute tolerance to be used for fuzzy comparisons."""
        self._array_predicate.absolute_tolerance = abs_tol


def _get_equality_fail_message(val1, val2) -> str:
    return "{} and {} have compared unequal".format(
        _get_as_string(val1),
        _get_as_string(val2)
    )
