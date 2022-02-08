"""Classes and functions related to predicates on fields & arrays"""

from typing import Callable, Optional, TypeVar
from numpy import allclose

from ._common import _get_as_string, _default_base_tolerance, _is_iterable, _is_scalar

from .array import Array, is_array, make_array
from .array import find_first_unequal
from .array import find_first_fuzzy_unequal
from .array import rel_diff, abs_diff, max_column_elements


class PredicateResult:
    """Stores the result of a predicate evaluation"""
    def __init__(self,
                 value: bool,
                 report: str = "",
                 predicate_info: str = None) -> None:
        self._value = value
        self._report = report
        self._predicate_info = predicate_info

    def __bool__(self) -> bool:
        return self._value

    @property
    def report(self) -> str:
        """Return a report of the predicate evaluation."""
        return self._report

    @property
    def predicate_info(self) -> Optional[str]:
        """Return info string about the predicate that was used."""
        return self._predicate_info

    @property
    def value(self) -> bool:
        """Return the underlying boolean value"""
        return self._value


class ExactEquality:
    """Compares the given arguments for exact equality"""
    def __call__(self, first, second) -> PredicateResult:
        first_is_iterable = _is_iterable(first)
        second_is_iterable = _is_iterable(second)
        if first_is_iterable and second_is_iterable:
            return self._array_equal(
                first if is_array(first) else make_array(first),
                second if is_array(second) else make_array(second)
            )
        try:
            if first != second:
                return PredicateResult(
                    value=False,
                    predicate_info=self._get_info(),
                    report=_get_equality_fail_message(first, second)
                )
            return PredicateResult(
                value=True,
                predicate_info=self._get_info(),
                report=f"{first} and {second} have compared equal"
            )
        except Exception as e:
            raise ValueError(f"Could not check the given values for equality. Caught exception: {e}")

    def _get_info(self) -> str:
        return "ExactEquality"

    def _array_equal(self, first: Array, second: Array) -> PredicateResult:
        if len(first) != len(second):
            return PredicateResult(
                value=False,
                report="Array lengths not equal",
                predicate_info=self._get_info()
            )
        unequals = find_first_unequal(first, second)
        if unequals is not None:
            val1, val2 = unequals
            return PredicateResult(
                value=False,
                report=_get_equality_fail_message(val1, val2),
                predicate_info=self._get_info()
            )
        return PredicateResult(
            value=True,
            predicate_info=self._get_info(),
            report="All field values have compared equal"
        )


class FuzzyEquality:
    """Compares the given arguments for fuzzy equality"""
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
        return self._abs_tol

    @absolute_tolerance.setter
    def absolute_tolerance(self, value: float) -> None:
        """Set the absolute tolerance to be used for fuzzy comparisons."""
        self._abs_tol = value

    def __call__(self, first, second) -> PredicateResult:
        first_is_iterable = _is_iterable(first)
        second_is_iterable = _is_iterable(second)
        if first_is_iterable and second_is_iterable:
            return self._array_fuzzy_equal(
                first if is_array(first) else make_array(first),
                second if is_array(second) else make_array(second)
            )
        try:
            if _is_fuzzy_equal(first, second, self.absolute_tolerance, self.relative_tolerance):
                return PredicateResult(
                    value=True,
                    report=f"{first} and {second} have compared equal",
                    predicate_info=self._get_info()
                )
            deviation_in_percent = self._compute_deviation_in_percent(first, second)
            return PredicateResult(
                value=False,
                report=_get_equality_fail_message(first, second, deviation_in_percent),
                predicate_info=self._get_info()
            )
        except Exception as e:
            raise ValueError(f"Could not fuzzy-compare the given values. Caught exception: {e}")

    def _array_fuzzy_equal(self, first: Array, second: Array) -> PredicateResult:
        if len(first) != len(second):
            return PredicateResult(
                value=False,
                report="Array lengths not equal",
                predicate_info=self._get_info()
            )
        unequals = find_first_fuzzy_unequal(first, second, self._rel_tol, self._abs_tol)
        if unequals is not None:
            val1, val2 = unequals
            deviation_in_percent = self._compute_deviation_in_percent(val1, val2)
            return PredicateResult(
                value=False,
                report=_get_equality_fail_message(val1, val2, deviation_in_percent),
                predicate_info=self._get_info()
            )

        max_abs_diffs = self._compute_max_abs_diffs(first, second)
        if max_abs_diffs is not None:
            diff_suffix = "s" if is_array(max_abs_diffs) else ""
            max_abs_diff_str = _get_as_string(max_abs_diffs)
            max_abs_diff_str = max_abs_diff_str.replace("\n", " ")
            return PredicateResult(
                value=True,
                report="Maximum absolute difference{}: {}".format(diff_suffix, max_abs_diff_str),
                predicate_info=self._get_info()
            )
        return PredicateResult(True, predicate_info=self._get_info())

    def _get_info(self) -> str:
        return "FuzzyEquality (abs_tol: {}, rel_tol: {})".format(
            self.absolute_tolerance,
            self.relative_tolerance
        )

    def _compute_deviation_in_percent(self, val1, val2):
        try:
            return rel_diff(val1, val2)*100.0
        except Exception:
            return None

    def _compute_max_abs_diffs(self, first, second):
        try:
            return max_column_elements(abs_diff(first, second))
        except Exception:
            return None


class DefaultEquality(FuzzyEquality):
    """Default choice of quality checks. Checks fuzzy or exact depending on data type."""
    def __init__(self, *args, **kwargs) -> None:
        FuzzyEquality.__init__(self, *args, **kwargs)

    def __call__(self, first, second) -> PredicateResult:
        if _is_float(first) or _is_float(second):
            return FuzzyEquality.__call__(self, first, second)
        return ExactEquality()(first, second)


T1 = TypeVar("T1")
T2 = TypeVar("T2")
Predicate = Callable[[T1, T2], PredicateResult]


def _is_float(value) -> bool:
    if _is_scalar(value):
        return isinstance(value, float)
    elif _is_iterable(value):
        return any(_is_float(v) for v in value)
    return False


def _is_fuzzy_equal(first, second, abs_tol, rel_tol) -> bool:
    return allclose(first, second, rtol=rel_tol, atol=abs_tol)


def _get_equality_fail_message(val1, val2, deviation_in_percent=None) -> str:
    result = str(
        "Deviation above threshold detected:\n"
        "- First field entry: {}\n"
        "- Second field entry: {}".format(
            _get_as_string(val1),
            _get_as_string(val2)
        )
    )
    if deviation_in_percent is not None:
        result += f"\n- Deviation in [%]: {deviation_in_percent}"
    return result
