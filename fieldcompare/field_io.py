"""Read fields from files with various data formats"""

from os.path import splitext, exists

from .field import FieldContainer
from .logging import Logger, NullDeviceLogger

from ._field_io import _get_reader_for_extension, FieldReader, _mesh_io


def is_mesh_file(filename: str) -> bool:
    return splitext(filename)[1] in _mesh_io.supported_extensions


def read_fields(filename: str, logger: Logger = NullDeviceLogger()) -> FieldContainer:
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
