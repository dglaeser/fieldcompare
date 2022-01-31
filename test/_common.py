"""Common functionality needed in the test suite"""

from context import fieldcompare
from fieldcompare import Field, ExactEquality, FuzzyEquality, DefaultEquality

class ExactFieldEquality:
    def __init__(self, require_equal_names=True):
        self._require_equal_names = require_equal_names

    def __call__(self, field1: Field, field2: Field) -> bool:
        if self._require_equal_names and field1.name != field2.name:
            return False
        return bool(ExactEquality()(field1.values, field2.values))


class FuzzyFieldEquality:
    def __init__(self, require_equal_names=True):
        self._require_equal_names = require_equal_names
        self._abs_tol = None
        self._rel_tol = None

    def set_relative_tolerance(self, value: float) -> None:
        self._rel_tol = value

    def set_absolute_tolerance(self, value: float) -> None:
        self._abs_tol = value

    def __call__(self, field1: Field, field2: Field) -> bool:
        if self._require_equal_names and field1.name != field2.name:
            return False
        predicate = FuzzyEquality()
        if self._abs_tol is not None:
            predicate.absolute_tolerance = self._abs_tol
        if self._rel_tol is not None:
            predicate.relative_tolerance = self._rel_tol
        return bool(predicate(field1.values, field2.values))

class DefaultFieldEquality(FuzzyFieldEquality):
    def __init__(self, *args, **kwargs) -> None:
        FuzzyFieldEquality.__init__(self, *args, **kwargs)

    def __call__(self, field1: Field, field2: Field) -> bool:
        if self._require_equal_names and field1.name != field2.name:
            return False
        predicate = DefaultEquality()
        if self._abs_tol is not None:
            predicate.absolute_tolerance = self._abs_tol
        if self._rel_tol is not None:
            predicate.relative_tolerance = self._rel_tol
        return bool(predicate(field1.values, field2.values))
