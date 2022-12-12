"""
The fieldcompare module

Prodives a framework to compare fields of values for relational properties as e.g. equality.
This can be useful, for instance, in regression-testing simulation software, comparing simulation
results against previously obtained results.
"""

from .__about__ import __version__

from ._array import (
    Array,
    sub_array,
    make_array,
    make_initialized_array,
    make_uninitialized_array
)

from ._field import (
    Field,
    FieldInterface,
    FieldContainer,
    FieldContainerInterface
)

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

from ._field_sequence import FieldDataSequence
