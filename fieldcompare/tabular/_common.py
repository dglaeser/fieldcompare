"""Common helper functions for io operations from tabular data formats"""


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
