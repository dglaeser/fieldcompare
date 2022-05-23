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

from ._predicates import (
    ExactEquality,
    FuzzyEquality,
    DefaultEquality
)

from ._field import (
    Field,
    FieldInterface,
    FieldContainer,
    FieldContainerInterface
)

from ._field_io import (
    read_fields,
    make_field_reader,
    make_mesh_field_reader,
    is_supported_file,
    is_mesh_file
)

from ._logging import (
    NullDeviceLogger,
    StandardOutputLogger,
    StreamLogger,
    LoggerBase,
    LoggableBase,
    LoggerInterface,
    Loggable
)
