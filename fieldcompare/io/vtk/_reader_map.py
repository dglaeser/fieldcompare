from typing import Dict, Protocol, Union
from ... import protocols


class _FieldDataReader(Protocol):
    def read(self) -> Union[protocols.FieldData, protocols.FieldDataSequence]:
        ...


class _VTKReader(Protocol):
    def __call__(self, filename: str) -> _FieldDataReader:
        ...


_VTK_EXTENSION_TO_READER: Dict[str, _VTKReader] = {}
