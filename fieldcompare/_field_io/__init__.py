from copy import deepcopy
from os.path import exists, splitext
from typing import Optional, Protocol, runtime_checkable

from .._logging import LoggerInterface, NullDeviceLogger, Loggable
from .._field import FieldContainerInterface
from .._mesh_fields import MeshFieldContainerInterface

from . import _csv, _mesh_io


class FieldReaderInterface(Loggable, Protocol):
    """Interface for readers for fields from files"""
    def read(self, filename: str) -> FieldContainerInterface:
        ...


@runtime_checkable
class MeshFieldReaderInterface(Loggable, Protocol):
    """Interface for readers for fields from mesh files"""
    def read(self, filename: str) -> MeshFieldContainerInterface:
        ...

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
def _get_reader_for_extension(extension: str) -> Optional[FieldReaderInterface]:
    return _EXTENSION_TO_READER_MAP.get(extension)


def _register_reader_for_extension(extension: str, reader: FieldReaderInterface) -> None:
    _EXTENSION_TO_READER_MAP[extension] = reader


# register the readers for the different formats
_csv._register_readers_for_extensions(_register_reader_for_extension)
_mesh_io._register_readers_for_extensions(_register_reader_for_extension)


def is_mesh_file(filename: str) -> bool:
    try:
        _get_mesh_field_reader(filename)
        return True
    except ValueError:
        return False


def read_fields(filename: str, logger: LoggerInterface = NullDeviceLogger()) -> FieldContainerInterface:
    """Read in the fields from the file with the given name using default settings"""
    if not exists(filename):
        raise IOError(f"Given file '{filename}' does not exist")

    reader = _get_field_reader(filename)
    reader.attach_logger(logger)
    fields = reader.read(filename)
    reader.remove_logger(logger)
    return fields


def make_field_reader(filename: str) -> FieldReaderInterface:
    """Returng a reader suitable for reading fields from the given file"""
    return deepcopy(_get_field_reader(filename))


def make_mesh_field_reader(filename: str) -> MeshFieldReaderInterface:
    """Return a configurable mesh field reader for the given mesh file"""
    return deepcopy(_get_mesh_field_reader(filename))


def is_supported_file(filename: str) -> bool:
    """Return true if field I/O from the given file is supported"""
    return _get_reader_for_extension(splitext(filename)[1]) is not None


def _get_field_reader(filename: str) -> FieldReaderInterface:
    file_extension = splitext(filename)[1]
    if not file_extension:
        raise ValueError("Could not get extension from given filename")

    reader = _get_reader_for_extension(file_extension)
    if reader is None:
        raise NotImplementedError(f"No reader found for files with the extension {file_extension}")
    return reader


def _get_mesh_field_reader(filename: str) -> MeshFieldReaderInterface:
    reader = _get_field_reader(filename)
    if not isinstance(reader, MeshFieldReaderInterface):
        raise ValueError("Reader found for the given file is not a mesh field reader")
    return reader
