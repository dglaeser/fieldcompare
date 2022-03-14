"""Maps to extensions a suitable reader, to be filled by implementations."""

from typing import Iterable, Protocol
from ..field import FieldInterface
from ..logging import Loggable

_EXTENSION_TO_READER_MAP: dict = {}

class FieldReader(Loggable, Protocol):
    def read(self, filename: str) -> Iterable[FieldInterface]:
        ...

def _register_reader_for_extension(extension: str, reader: FieldReader) -> None:
    _EXTENSION_TO_READER_MAP[extension] = reader
