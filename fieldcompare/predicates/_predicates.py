"""Predicate classes for comparing arrays"""

from dataclasses import dataclass

from .._common import _default_base_tolerance

from .._numpy_utils import ArrayLike, as_array, as_string, has_floats
from .._numpy_utils import find_first_unequal
from .._numpy_utils import find_first_fuzzy_unequal
from .._numpy_utils import rel_diff, abs_diff, max_column_elements


class PredicateError(Exception):
    """Exception raised for errors during predicate evaluation"""
    pass


@dataclass
class PredicateResult:
    value: bool
    report: str = ""

    def __bool__(self) -> bool:
        return self.value


class ExactEquality:
    """Compares the given arrays for exact equality"""
    def __call__(self, first: ArrayLike, second: ArrayLike) -> PredicateResult:
        try:
            return self._check(first, second)
        except Exception as e:
            raise PredicateError(f"Exact equality check failed with exception: {e}\n")

    def __str__(self) -> str:
        return "ExactEquality"

    def _check(self, first: ArrayLike, second: ArrayLike) -> PredicateResult:
        first = as_array(first)
        second = as_array(second)
        if first.shape != second.shape:
            return PredicateResult(
                value=False,
                report=f"Array shapes not equal: {first.shape} / {second.shape}"
            )
        unequals = find_first_unequal(first, second)
        if unequals is not None:
            val1, val2 = unequals
            return PredicateResult(
                value=False,
                report=_get_equality_fail_report(val1, val2),
            )
        return _success_result()


class FuzzyEquality:
    """Compares the given arrays for fuzzy equality"""
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

    def __call__(self, first: ArrayLike, second: ArrayLike) -> PredicateResult:
        try:
            return self._check(first, second)
        except Exception as e:
            raise PredicateError(f"Fuzzy comparison failed with exception: {e}")

    def __str__(self) -> str:
        return "FuzzyEquality (abs_tol: {}, rel_tol: {})".format(
            self.absolute_tolerance,
            self.relative_tolerance
        )

    def _check(self, first: ArrayLike, second: ArrayLike) -> PredicateResult:
        first = as_array(first)
        second = as_array(second)
        if first.shape != second.shape:
            return PredicateResult(
                value=False,
                report=f"Array shapes not equal: {first.shape} / {second.shape}"
            )
        unequals = find_first_fuzzy_unequal(first, second, self._rel_tol, self._abs_tol)
        if unequals is not None:
            val1, val2 = unequals
            deviation_in_percent = _compute_deviation_in_percent(val1, val2)
            return PredicateResult(
                value=False,
                report=_get_equality_fail_report(val1, val2, deviation_in_percent)
            )
        max_abs_diffs = _compute_max_abs_diffs(first, second)
        if max_abs_diffs is not None:
            max_abs_diff_str = as_string(max_abs_diffs)
            max_abs_diff_str = max_abs_diff_str.replace("\n", " ")
            return PredicateResult(
                value=True,
                report="Maximum absolute difference: {}".format(max_abs_diff_str)
            )
        return _success_result()


class DefaultEquality(FuzzyEquality):
    """Default choice for equality predicates. Checks fuzzy or exact depending on the data type."""
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def __call__(self, first, second) -> PredicateResult:
        first = as_array(first)
        second = as_array(second)
        if has_floats(first) or has_floats(second):
            return FuzzyEquality.__call__(self, first, second)
        return ExactEquality()(first, second)

    def __str__(self) -> str:
        return "DefaultEquality (abs_tol: {}, rel_tol: {})".format(
            self.absolute_tolerance,
            self.relative_tolerance
        )


def _get_equality_fail_report(val1, val2, deviation_in_percent=None) -> str:
    result = f"Deviation above tolerance detected -> {as_string(val1)} vs. {as_string(val2)}"
    if deviation_in_percent is not None:
        result += f" ({as_string(deviation_in_percent, digits=2)} %)"
    return result


def _compute_deviation_in_percent(val1, val2):
    try:
        return rel_diff(val1, val2)*100.0
    except Exception:
        return None


def _compute_max_abs_diffs(first, second):
    try:
        return max_column_elements(abs_diff(first, second))
    except Exception:
        return None


def _success_result() -> PredicateResult:
    return PredicateResult(
        True,
        report="All field values have compared equal"
    )
