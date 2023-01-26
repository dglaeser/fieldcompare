# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

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
