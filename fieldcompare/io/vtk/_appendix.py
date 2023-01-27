# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

from ._encoders import Encoder, NoEncoder, Base64Encoder


class VTKXMLAppendix:
    def __init__(self, content: bytes, encoding: str) -> None:
        self._content = content
        self._encoding = encoding

    @property
    def encoder(self) -> Encoder:
        if self._encoding == "base64":
            return Base64Encoder()
        if self._encoding == "raw":
            return NoEncoder()
        raise NotImplementedError(f"Unupported encoding '{self._encoding}'")

    def get(self, offset: int = 0) -> bytes:
        return self._content[offset:]
