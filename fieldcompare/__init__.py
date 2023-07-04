# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
fieldcompare provides functionality to compare field data, where field data are collections of
fields (each consisting of a name and an associated array of values) defined on domains. An example
would be discrete numerical solutions (fields) defined on a computational mesh (domain). This top-level
module exposes central classes in this context, mostly operating on the protocols defined in the "protocols"
module. Implementations of these protocols can be found in the submodules.
"""

from .__about__ import __version__

from ._field_sequence import FieldDataSequence
from ._field_data_comparison import (
    FieldDataComparator,
    FieldComparisonSuite,
    FieldComparison,
    FieldComparisonStatus,
    DefaultFieldComparisonCallback,
    field_comparison_report,
)

__all__ = [
    "DefaultFieldComparisonCallback",
    "FieldDataComparator",
    "FieldComparisonSuite",
    "FieldComparison",
    "FieldComparisonStatus",
    "FieldDataSequence",
    "field_comparison_report",
    "__version__",
]
