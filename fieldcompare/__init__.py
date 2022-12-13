"""
The fieldcompare module

Prodives a framework to compare fields of values for relational properties as e.g. equality.
This can be useful, for instance, in regression-testing simulation software, comparing simulation
results against previously obtained results.
"""

from .__about__ import __version__

from ._field import Field
from ._field_sequence import FieldDataSequence

from ._matching import (
    find_matches,
    find_matches_by_name,
    find_matching_file_names
)

from ._comparisons import (
    FieldDataComparison,
    FieldComparisonStatus,
    FieldComparisonResult,
    FieldComparisonSuite
)
