"""A map from file extensions to suitable readers, to be filled by reader implementations."""

from typing import Protocol, Optional
from ..field import FieldContainer
from ..logging import Loggable

class FieldReader(Loggable, Protocol):
    def read(self, filename: str) -> FieldContainer:
        ...


_EXTENSION_TO_READER_MAP: dict = {}


def _get_reader_for_extension(extension: str) -> Optional[FieldReader]:
    return _EXTENSION_TO_READER_MAP.get(extension)


def _register_reader_for_extension(extension: str, reader: FieldReader) -> None:
    _EXTENSION_TO_READER_MAP[extension] = reader
