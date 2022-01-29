"""Classes and functions related to predicates on fields & arrays"""

from typing import Callable, Optional

from ._common import _get_as_string
from ._common import _default_base_tolerance

from .array import Array, sub_array, is_array, make_array
from .array import find_first_unequal
from .array import find_first_fuzzy_unequal
from .array import rel_diff, abs_diff, max_column_elements
from .field import FieldInterface


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


class ExactArrayEquality:
    """Compares two arrays for exact equality"""
    def __call__(self, first: Array, second: Array) -> PredicateResult:
        first = make_array(first) if not is_array(first) else first
        second = make_array(second) if not is_array(second) else second
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

    def _get_info(self) -> str:
        return "ExactEquality"


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
        return self._abs_tol

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
                 require_equal_names: bool = False,
                 require_equal_lengths: bool = True) -> None:
        self._array_predicate = array_predicate
        self._require_equal_names = require_equal_names
        self._require_equal_lengths = require_equal_lengths

    def __call__(self, first: FieldInterface, second: FieldInterface) -> PredicateResult:
        if self._require_equal_names and first.name != second.name:
            return PredicateResult(
                False,
                f"Field name mismatch: {first.name} - {second.name}"
            )

        if len(first.values) == len(second.values):
            return self._array_predicate(first.values, second.values)

        if self._require_equal_lengths:
            return PredicateResult(
                False,
                f"Field length mismatch: {len(first.values)} - {len(second.values)}"
            )

        min_len = min(len(first.values), len(second.values))
        return self._array_predicate(
            sub_array(first.values, 0, min_len),
            sub_array(second.values, 0, min_len)
        )


class ExactFieldEquality(FieldPredicate):
    """Compare two fields for exact equality"""
    def __init__(self,
                 require_equal_names: bool = True,
                 require_equal_lengths: bool = True) -> None:
        FieldPredicate.__init__(
            self, ExactArrayEquality(), require_equal_names, require_equal_lengths
        )


class FuzzyFieldEquality(FieldPredicate):
    """Compare two fields for fuzzy equality"""
    def __init__(self,
                 require_equal_names: bool = True,
                 require_equal_lengths: bool = True) -> None:
        FieldPredicate.__init__(
            self, FuzzyArrayEquality(), require_equal_names, require_equal_lengths
        )

    def set_relative_tolerance(self, rel_tol: float) -> None:
        """Set the relative tolerance to be used for fuzzy comparisons."""
        self._array_predicate.relative_tolerance = rel_tol

    def set_absolute_tolerance(self, abs_tol: float) -> None:
        """Set the absolute tolerance to be used for fuzzy comparisons."""
        self._array_predicate.absolute_tolerance = abs_tol


class DefaultFieldEquality(FieldPredicate):
    """Default implementation for field equality. Checks fuzzy or exact depending on data type."""
    def __init__(self,
                 require_equal_names: bool = True,
                 require_equal_lengths: bool = True) -> None:
        FieldPredicate.__init__(
            self, DefaultArrayEquality(), require_equal_names, require_equal_lengths
        )

    def set_relative_tolerance(self, rel_tol: float) -> None:
        """Set the relative tolerance to be used for fuzzy comparisons."""
        self._array_predicate.relative_tolerance = rel_tol

    def set_absolute_tolerance(self, abs_tol: float) -> None:
        """Set the absolute tolerance to be used for fuzzy comparisons."""
        self._array_predicate.absolute_tolerance = abs_tol


def _get_equality_fail_message(val1, val2, deviation_in_percent = None) -> str:
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
