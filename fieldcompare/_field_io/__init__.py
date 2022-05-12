from os.path import exists, splitext
from typing import Optional, Protocol

from ..logging import Logger, NullDeviceLogger, Loggable
from ..field import FieldContainer

from . import _csv, _mesh_io


class FieldReader(Loggable, Protocol):
    """Interface for readers for fields from files"""
    def read(self, filename: str) -> FieldContainer:
        ...


class MeshFieldReader(FieldReader, Protocol):
    """Interface for readers for fields from mesh files"""
    @property
    def remove_ghost_points(self) -> bool:
        ...

    @remove_ghost_points.setter
    def remove_ghost_points(self, value: bool) -> None:
        ...

    @property
    def permute_uniquely(self) -> bool:
        ...

    @permute_uniquely.setter
    def permute_uniquely(self, value: bool) -> None:
        ...


_EXTENSION_TO_READER_MAP: dict = {}
def _get_reader_for_extension(extension: str) -> Optional[FieldReader]:
    return _EXTENSION_TO_READER_MAP.get(extension)


def _register_reader_for_extension(extension: str, reader: FieldReader) -> None:
    _EXTENSION_TO_READER_MAP[extension] = reader


# register the readers for the different formats
_csv._register_readers_for_extensions(_register_reader_for_extension)
_mesh_io._register_readers_for_extensions(_register_reader_for_extension)


def is_mesh_file(filename: str) -> bool:
    return splitext(filename)[1] in _mesh_io.supported_extensions


def read_fields(filename: str, logger: Logger = NullDeviceLogger()) -> FieldContainer:
    """Read in the fields from the file with the given name using default settings"""
    if not exists(filename):
        raise IOError(f"Given file '{filename}' does not exist")

    reader = get_field_reader(filename)
    reader.attach_logger(logger)
    return reader.read(filename)


def get_field_reader(filename: str) -> FieldReader:
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
