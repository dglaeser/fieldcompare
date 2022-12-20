from typing import Dict, Protocol, Union, runtime_checkable
from ... import protocols


@runtime_checkable
class _FieldDataReader(Protocol):
    def read(self) -> Union[protocols.FieldData, protocols.FieldDataSequence]:
        ...


@runtime_checkable
class _VTKReader(Protocol):
    def __call__(self, filename: str) -> _FieldDataReader:
        ...


class _Map:
    def __init__(self) -> None:
        self._map: Dict[str, _VTKReader] = {}

    def __getitem__(self, key: str) -> _VTKReader:
        return self._map[key]

    def __setitem__(self, key: str, value: _VTKReader) -> None:
        assert isinstance(value, _VTKReader)
        self._map[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._map


_VTK_EXTENSION_TO_READER = _Map()
