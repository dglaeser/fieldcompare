"""
The fieldcompare module

Prodives a framework fields of values for relational properties as e.g. equality.
This can be used e.g. in regression testing simulation software, comparing simulation
results against previously obtained results.
"""

from .__about__ import __version__
from .array import Array, sub_array, make_array, make_initialized_array, make_uninitialized_array
from .field import Field, FieldInterface
from .predicates import ExactArrayEquality, FuzzyArrayEquality, DefaultArrayEquality
from .predicates import ExactFieldEquality, FuzzyFieldEquality, DefaultFieldEquality
from .field_io import read_fields
from .compare import compare_fields
