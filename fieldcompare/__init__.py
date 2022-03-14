"""
The fieldcompare module

Prodives a framework to compare fields of values for relational properties as e.g. equality.
This can be useful, for instance, in regression-testing simulation software, comparing simulation
results against previously obtained results.
"""

from .__about__ import __version__

from .array import Array, sub_array, make_array, make_initialized_array, make_uninitialized_array
from .predicates import ExactEquality, FuzzyEquality, DefaultEquality

from .field import Field, FieldInterface
from .field_io import read_fields, is_supported_file, make_reader
from ._field_io._csv import CSVFieldReader
from ._field_io._mesh_io import MeshFieldReader
