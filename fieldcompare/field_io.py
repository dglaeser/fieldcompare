"""Read fields from files with various data formats"""

from os.path import splitext, exists
from typing import Iterable

from .field import FieldInterface
from ._field_io import _get_reader_for_extension, FieldReader
from .logging import Logger, NullDeviceLogger


def read_fields(filename: str,
                logger: Logger = NullDeviceLogger()) -> Iterable[FieldInterface]:
    """Read in the fields from the file with the given name using default settings"""
    if not exists(filename):
        raise IOError(f"Given file '{filename}' does not exist")

    reader = make_reader(filename)
    reader.attach_logger(logger)
    return reader.read(filename)


def make_reader(filename: str) -> FieldReader:
    """Returng a configurable reader suitable for reading fields from the given file"""
    file_extension = splitext(filename)[1]
    if not file_extension:
        raise ValueError("Could not get extension from given filename")

    reader = _get_reader_for_extension(file_extension)
    if reader is None:
        raise NotImplementedError(f"No reader found for files with the extension {file_extension}")
    return reader


def is_supported_file(filename: str) -> bool:
    """Return true if field I/O from the given file is supported"""
    return _get_reader_for_extension(splitext(filename)[1]) is not None
