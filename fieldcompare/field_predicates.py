"""Predicate classes for comparing fields for equality"""

from abc import abstractmethod

from fieldcompare._common import Array, eq_exact, eq_bitset_exact, first_false_index
from fieldcompare.field import FieldInterface

class PredicateResult:
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


class FieldPredicate:
    def __init__(self,
                 ignore_names_mismatch: bool = False,
                 ignore_length_mismatch: bool = False) -> None:
        self._ignore_names_mismatch = ignore_names_mismatch
        self._ignore_length_mismatch = ignore_length_mismatch

    def __call__(self, first: FieldInterface, second: FieldInterface) -> PredicateResult:
        if not self._ignore_length_mismatch and len(first.values) != len(second.values):
            return PredicateResult(False, "Lengths do not match")
        if not self._ignore_names_mismatch and first.name != second.name:
            return PredicateResult(False, "Names do not match")
        return self._check_field_values(first, second)

    @abstractmethod
    def _check_field_values(self, first: FieldInterface, second: FieldInterface) -> PredicateResult:
        """Evaluate the field values for equality"""


class ExactFieldEquality(FieldPredicate):
    def _check_field_values(self, first: FieldInterface, second: FieldInterface) -> PredicateResult:
        if isinstance(first.values, Array) and isinstance(second.values, Array):
            return self._check_eq_arrays(first.values, second.values)
        raise NotImplementedError("ExactFieldEqualityCheck for non-array value types")

    def _check_eq_arrays(self, first: Array, second: Array) -> PredicateResult:
        if not eq_exact(first, second):
            idx = first_false_index(eq_bitset_exact(first, second))
            return PredicateResult(
                False, _binary_eq_fail_message(first[idx], second[idx])
            )
        return PredicateResult(True)


def _binary_eq_fail_message(first, second) -> str:
    return f"'{first}' and '{second}' have compared unequal."
