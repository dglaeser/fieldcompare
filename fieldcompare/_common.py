"""Common functions and types"""

from numpy import floating as _numpy_float
from numpy import ndarray as _numpy_array
from numpy import format_float_scientific as _numpy_format_scientific
from numpy import printoptions as _numpy_print_options
from numpy import array2string as _numpy_array_to_string

def _get_as_string(obj) -> str:
    if isinstance(obj, (_numpy_float, float)):
        return _numpy_format_scientific(obj, unique=True)
    elif isinstance(obj, _numpy_array):
        with _numpy_print_options(floatmode="unique") as opts:
            return _numpy_array_to_string(obj)
    return str(obj)

def _default_base_tolerance() -> float:
    return 1e-9
