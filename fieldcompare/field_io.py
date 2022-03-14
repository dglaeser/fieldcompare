"""Read fields from files with various data formats"""

from os.path import splitext, exists
from typing import Iterable, Optional

from .field import FieldInterface
from ._field_io import _get_reader_for_extension, FieldReader
from .logging import Logger, NullDeviceLogger


def read_fields(filename: str,
                logger: Logger = NullDeviceLogger()) -> Iterable[FieldInterface]:
    """Read in the fields from the file with the given name using default settings"""
    if not exists(filename):
        raise IOError(f"Given file '{filename}' does not exist")

    ext = splitext(filename)[1]
    reader = make_reader(ext)
    if reader is None:
        raise NotImplementedError(f"No reader found for files with the extension {ext}")
    reader.attach_logger(logger)
    return reader.read(filename)


def make_reader(file_extension: str) -> Optional[FieldReader]:
    """Returng a further configurable reader suitable for the given file extension"""
    if not file_extension.startswith("."):
        file_extension = f".{file_extension}"
    return _get_reader_for_extension(file_extension)


def is_supported_file(filename: str) -> bool:
    """Return true if field I/O from the given file(type) is supported"""
    return make_reader(splitext(filename)[1]) is not None
