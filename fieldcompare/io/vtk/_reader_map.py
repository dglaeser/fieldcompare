# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations
from typing import Protocol, runtime_checkable
from ... import protocols


@runtime_checkable
class _FieldDataReader(Protocol):
    def read(self) -> protocols.FieldData | protocols.FieldDataSequence:
        ...


@runtime_checkable
class _VTKReader(Protocol):
    def __call__(self, filename: str) -> _FieldDataReader:
        ...


class _Map:
    def __init__(self) -> None:
        self._map: dict[str, _VTKReader] = {}

    def __getitem__(self, key: str) -> _VTKReader:
        return self._map[key]

    def __setitem__(self, key: str, value: _VTKReader) -> None:
        assert isinstance(value, _VTKReader)
        self._map[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._map


_VTK_EXTENSION_TO_READER = _Map()
_VTK_TYPE_TO_EXTENSION: dict[str, str] = {}
