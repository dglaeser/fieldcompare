"""Maps to extensions a suitable reader, to be filled by implementations."""

from typing import Callable, Iterable
from ..field import FieldInterface
from ..logging import Logger

_EXTENSION_TO_READER_MAP: dict = {}

FieldReader = Callable[[str, bool, Logger], Iterable[FieldInterface]]
def _register_reader_for_extension(extension: str, reader: FieldReader) -> None:
    _EXTENSION_TO_READER_MAP[extension] = reader
