"""Predicate classes for comparing fields for equality"""

from abc import abstractmethod

from fieldcompare._common import Array
from fieldcompare._common import check_arrays_equal
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
        if not self._ignore_length_mismatch:
            if len(first.values) != len(second.values):
                return PredicateResult(False, "Lengths do not match")
        if not self._ignore_names_mismatch:
            if first.name != second.name:
                return PredicateResult(False, "Names do not match")
        return self._check_field_values(first, second)

    @abstractmethod
    def _check_field_values(self, first: FieldInterface, second: FieldInterface) -> PredicateResult:
        """Evaluate the field values for equality"""

class ExactFieldEquality(FieldPredicate):
    def _check_field_values(self, first: FieldInterface, second: FieldInterface) -> PredicateResult:
        if isinstance(first, Array) and isinstance(second, Array):
            eq_bitset = check_arrays_equal(first, second)
            if not all(eq_bitset):
                for idx, value in eq_bitset:
                    if not value:
                        return PredicateResult(False, f"{first.values[idx]} and {second.values[idx]} have compared unequal.")
        else:
            for val1, val2 in zip(first.values, second.values):
                if val1 != val2:
                    return PredicateResult(False, f"{val1} and {val2} have compared unequal.")
        return PredicateResult(True)

