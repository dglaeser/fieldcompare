from base64 import b64decode
from typing import Protocol


class Decoder(Protocol):
    def decode(self, data: bytes) -> bytes:
        ...

    def encoded_size(self, decoded_size: int) -> int:
        ...


class NoDecoder:
    def decode(self, data: bytes) -> bytes:
        return data

    def encoded_size(self, decoded_size: int) -> int:
        return int(decoded_size)


class Base64Decoder:
    def decode(self, data: bytes) -> bytes:
        return b64decode(data, validate=True)

    def encoded_size(self, decoded_size: int) -> int:
        if not isinstance(decoded_size, int):
            decoded_size = int(decoded_size)
        # see https://github.com/nschloe/meshio/blob/0138cc8692b806b44b32d344f7961e8370121ff7/src/meshio/vtu/_vtu.py#L27
        return -(-decoded_size // 3) * 4
