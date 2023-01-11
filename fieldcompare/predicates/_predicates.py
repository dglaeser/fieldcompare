"""Predicate classes for comparing arrays"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, Optional, Union

from .._common import _default_base_tolerance
from ..protocols import ToleranceEstimator

from .._numpy_utils import ArrayTolerance, ArrayLike, Array, as_array, as_string, has_floats
from .._numpy_utils import find_first_unequal
from .._numpy_utils import find_first_fuzzy_unequal
from .._numpy_utils import rel_diff, abs_diff
from .._numpy_utils import max_column_elements, max_abs_element, max_abs_value, select_max_values


class PredicateError(Exception):
    """Exception raised for errors during predicate evaluation"""

    pass


class AbsoluteToleranceEstimator:
    f"""
    Estimates a suitable absolute tolerance for comparing two fields by scaling the
    maximum ocurring value in the two fields (as an estimate for their magnitude)
    with a given relative tolerance.

    Args:
        rel_tol: The relative tolerance with which to scale the magnitude (default: {_default_base_tolerance()})
        use_component_magnitudes: If true, the magnitudes are determined separately for each component,
                                  and if per-component tolerances are given, they are scaled individually
    """

    def __init__(
        self, rel_tol: ArrayTolerance = _default_base_tolerance(), use_component_magnitudes: Optional[bool] = False
    ) -> None:
        self._rel_tol = as_array(rel_tol)
        self._use_component_magnitudes = use_component_magnitudes

    def __call__(self, first: Array, second: Array) -> ArrayTolerance:
        """Return an estimate for the absolute tolerance for comparing the given fields."""
        if self._use_component_magnitudes:
            return select_max_values(max_abs_element(first), max_abs_element(second)) * self._rel_tol
        return self._rel_tol * max(max_abs_value(first), max_abs_value(second))

    def __str__(self) -> str:
        return f"AbsoluteToleranceEstimator (rel_tol={self._rel_tol})"


@dataclass
class PredicateResult:
    """Contains the result of a predicate evaluation."""

    value: bool
    report: str = ""

    def __bool__(self) -> bool:
        """Return true if the predicate evaluation is considered successful"""
        return self.value


class ExactEquality:
    """Compares arrays for exact equality"""

    def __call__(self, first: ArrayLike, second: ArrayLike) -> PredicateResult:
        """
        Evaluate the predicate for the two given arrays:

        Args:
            first: The first array.
            second: The second array.
        """
        try:
            return self._check(first, second)
        except Exception as e:
            raise PredicateError(f"Exact equality check failed with exception: {e}\n")

    def __str__(self) -> str:
        return "ExactEquality"

    def _check(self, first: ArrayLike, second: ArrayLike) -> PredicateResult:
        first, second = _reshape(first, second)
        shape_check = _check_shapes(first, second)
        if not shape_check:
            return shape_check

        unequals = find_first_unequal(first, second)
        if unequals is not None:
            val1, val2 = unequals
            return PredicateResult(
                value=False,
                report=_get_equality_fail_report(val1, val2),
            )
        return _success_result()


class FuzzyEquality:
    """
    Compares arrays for fuzzy equality.
    Arrays are considered fuzzy equal if for each pair of scalars the following relation holds:
    `abs(a - b) <= max(_rtol*max(a, b), _atol)`. Note that tolerances can either be given as `float`
    values, in which case `_rtol = rel_tol` and `_atol = abs_tol`, or, as instances of :class:`.ToleranceEstimator`,
    in which case the actually used values are determined from the fields to be compared.

    Args:
        rel_tol: The relative tolerance to be used.
        abs_tol: The absolute tolerance to be used.
    """

    def __init__(
        self,
        rel_tol: Union[ToleranceEstimator, ArrayTolerance] = _default_base_tolerance(),
        abs_tol: Union[ToleranceEstimator, ArrayTolerance] = 0.0,
    ) -> None:
        self._rel_tol = rel_tol
        self._abs_tol = abs_tol
        self._last_used_rel_tol: Optional[ArrayTolerance] = None
        self._last_used_abs_tol: Optional[ArrayTolerance] = None

    @property
    def relative_tolerance(self) -> Optional[ArrayTolerance]:
        """Return the relative tolerance used for fuzzy comparisons."""
        return None if isinstance(self._rel_tol, ToleranceEstimator) else self._rel_tol

    @relative_tolerance.setter
    def relative_tolerance(self, value: Union[ToleranceEstimator, ArrayTolerance]) -> None:
        """
        Set the relative tolerance to be used for fuzzy comparisons.

        Args:
            value: The relative tolerance to be used.
        """
        self._rel_tol = value

    @property
    def absolute_tolerance(self) -> Optional[ArrayTolerance]:
        """Return the absolute tolerance used for fuzzy comparisons."""
        return None if isinstance(self._abs_tol, ToleranceEstimator) else self._abs_tol

    @absolute_tolerance.setter
    def absolute_tolerance(self, value: Union[ToleranceEstimator, ArrayTolerance]) -> None:
        """
        Set the absolute tolerance to be used for fuzzy comparisons.

        Args:
            value: The absolute tolerance to be used.
        """
        self._abs_tol = value

    def __call__(self, first: ArrayLike, second: ArrayLike) -> PredicateResult:
        """
        Evaluate the predicate for the two given arrays:

        Args:
            first: The first array.
            second: The second array.
        """
        try:
            return self._check(first, second)
        except Exception as e:
            raise PredicateError(f"Fuzzy comparison failed with exception: {e}")

    def __str__(self) -> str:
        return f"FuzzyEquality ({self._tolerance_info()})"

    def _tolerance_info(self) -> str:
        def _tolinfo(tol, last_used) -> str:
            if isinstance(tol, ToleranceEstimator):
                return f"estimate (last used: {as_string(last_used) if last_used is not None else None})"
            return f"{as_string(tol)}"

        return (
            f"abs_tol: {_tolinfo(self._abs_tol, self._last_used_abs_tol)}, "
            f"rel_tol: {_tolinfo(self._rel_tol, self._last_used_rel_tol)}"
        )

    def _estimate_tol(self, tol, first: Array, second: Array) -> ArrayTolerance:
        if isinstance(tol, ToleranceEstimator):
            return tol(first, second)
        return tol

    def _check(self, first: ArrayLike, second: ArrayLike) -> PredicateResult:
        first, second = _reshape(first, second)
        shape_check = _check_shapes(first, second)
        if not shape_check:
            return shape_check

        self._last_used_rel_tol = self._estimate_tol(self._rel_tol, first, second)
        self._last_used_abs_tol = self._estimate_tol(self._abs_tol, first, second)
        unequals = find_first_fuzzy_unequal(first, second, self._last_used_rel_tol, self._last_used_abs_tol)
        if unequals is not None:
            val1, val2 = unequals
            deviation_in_percent = _compute_deviation_in_percent(val1, val2)
            return PredicateResult(value=False, report=_get_equality_fail_report(val1, val2, deviation_in_percent))
        max_abs_diffs = _compute_max_abs_diffs(first, second)
        if max_abs_diffs is not None:
            max_abs_diff_str = as_string(max_abs_diffs)
            max_abs_diff_str = max_abs_diff_str.replace("\n", " ")
            return PredicateResult(value=True, report="Maximum absolute difference: {}".format(max_abs_diff_str))
        return _success_result()


class DefaultEquality(FuzzyEquality):
    """Default choice for equality predicates. Checks fuzzy or exact depending on the data type."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def __call__(self, first, second) -> PredicateResult:
        """
        Evaluate the predicate for the two given arrays:

        Args:
            first: The first array.
            second: The second array.
        """
        first = as_array(first)
        second = as_array(second)
        if has_floats(first) or has_floats(second):
            return FuzzyEquality.__call__(self, first, second)
        return ExactEquality()(first, second)

    def __str__(self) -> str:
        return f"DefaultEquality ({self._tolerance_info()})"


def _get_equality_fail_report(val1, val2, deviation_in_percent=None) -> str:
    result = f"Deviation above tolerance detected -> {as_string(val1)} vs. {as_string(val2)}"
    if deviation_in_percent is not None:
        result += f" ({as_string(deviation_in_percent, digits=2)} %)"
    return result


def _compute_deviation_in_percent(val1, val2):
    try:
        return rel_diff(val1, val2) * 100.0
    except Exception:
        return None


def _compute_max_abs_diffs(first, second):
    try:
        return max_column_elements(abs_diff(first, second))
    except Exception:
        return None


def _success_result() -> PredicateResult:
    return PredicateResult(True, report="All field values have compared equal")


def _reshape(arr1: ArrayLike, arr2: ArrayLike) -> Tuple[Array, Array]:
    arr1 = as_array(arr1)
    arr2 = as_array(arr2)
    dim1 = len(arr1.shape)
    dim2 = len(arr2.shape)

    # reshape the arrays in case scalars are compared against 1d vectors
    if dim1 == dim2 + 1 and arr1.shape[-1] == 1:
        arr2 = arr2.reshape(*arr2.shape, 1)
    if dim2 == dim1 + 1 and arr2.shape[-1] == 1:
        arr1 = arr1.reshape(*arr1.shape, 1)

    return arr1, arr2


def _check_shapes(arr1: Array, arr2: Array) -> PredicateResult:
    if arr1.shape != arr2.shape:
        return PredicateResult(value=False, report=f"Array shapes not equal: {arr1.shape} / {arr2.shape}")
    return PredicateResult(True)
