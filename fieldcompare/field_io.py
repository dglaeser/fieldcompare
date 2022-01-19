"""Read fields from files with various data formats"""

from os.path import splitext, exists
from typing import Iterable

from .field import Field
from ._field_io import _get_reader_for_extension


def read_fields(filename: str, remove_ghost_points: bool = True) -> Iterable[Field]:
    """Read in the fields from the file with the given name"""
    if not exists(filename):
        raise IOError(f"Given file '{filename}' does not exist")

    ext = splitext(filename)[1]
    reader = _get_reader_for_extension(ext)
    if reader is None:
        raise NotImplementedError(f"No reader found for files with the extension {ext}")
    return reader(filename, remove_ghost_points)
