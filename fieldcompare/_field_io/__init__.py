from typing import Optional

from . import _csv, _json, _mesh_io
from ._reader_map import FieldReader
from ._reader_map import _EXTENSION_TO_READER_MAP


def _get_reader_for_extension(extension: str) -> Optional[FieldReader]:
    return _EXTENSION_TO_READER_MAP.get(extension)
