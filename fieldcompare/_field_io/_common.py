"""Common helper functions for field-io operations"""

from typing import Iterable
from .._common import _is_scalar


def _is_supported_field_data_format(field_values: Iterable) -> bool:
    return all(_is_scalar(value) for value in field_values)


def _convert_string(value_string: str):
    value = _string_to_int(value_string)
    if value is not None:
        return value
    value = _string_to_float(value_string)
    if value is not None:
        return value
    return value_string


def _string_to_int(value_string: str):
    try:
        return int(value_string)
    except ValueError:
        return None


def _string_to_float(value_string: str):
    try:
        return float(value_string)
    except ValueError:
        return None


def _convertible_to_float(value_string: str) -> bool:
    return _string_to_float(value_string) is not None
