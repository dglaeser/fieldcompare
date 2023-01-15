"""Predefined predicate classes for comparing field values."""

from ._predicates import (
    ExactEquality,
    FuzzyEquality,
    DefaultEquality,
    PredicateResult,
    PredicateError,
    ScaledTolerance,
)

__all__ = [
    "ExactEquality",
    "FuzzyEquality",
    "DefaultEquality",
    "PredicateResult",
    "PredicateError",
    "ScaledTolerance",
]
