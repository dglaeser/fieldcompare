"""Read fields from files with various data formats"""

from os.path import splitext, exists
from typing import Iterable

from .field import Field
from ._field_io import _get_reader_for_extension
from .logging import Logger, NullDeviceLogger


def read_fields(filename: str,
                remove_ghost_points: bool = True,
                logger: Logger = NullDeviceLogger()) -> Iterable[Field]:
    """Read in the fields from the file with the given name"""
    if not exists(filename):
        raise IOError(f"Given file '{filename}' does not exist")

    ext = splitext(filename)[1]
    reader = _get_reader_for_extension(ext)
    if reader is None:
        raise NotImplementedError(f"No reader found for files with the extension {ext}")
    return reader(filename, remove_ghost_points, logger)


def is_supported_file(filename: str) -> bool:
    """Return true if field I/O from the given file(type) is supported"""
    ext = splitext(filename)[1]
    reader = _get_reader_for_extension(ext)
    return reader is not None
