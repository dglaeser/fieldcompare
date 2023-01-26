# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

from base64 import b64decode, b64encode
from typing import Protocol


class Encoder(Protocol):
    def decode(self, data: bytes) -> bytes:
        ...

    def encode(self, data: bytes) -> bytes:
        ...

    def encoded_bytes(self, decoded_bytes: int) -> int:
        ...


class NoEncoder:
    def decode(self, data: bytes) -> bytes:
        return data

    def encode(self, data: bytes) -> bytes:
        return data

    def encoded_bytes(self, decoded_bytes: int) -> int:
        return decoded_bytes


class Base64Encoder:
    def decode(self, data: bytes) -> bytes:
        return b64decode(data)

    def encode(self, data: bytes) -> bytes:
        return b64encode(data)

    def encoded_bytes(self, decoded_bytes: int) -> int:
        # see https://github.com/nschloe/meshio/blob/0138cc8692b806b44b32d344f7961e8370121ff7/src/meshio/vtu/_vtu.py#L27
        decoded_bytes = int(decoded_bytes)
        return -(-decoded_bytes // 3) * 4
