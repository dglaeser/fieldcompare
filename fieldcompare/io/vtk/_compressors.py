# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

import abc
import zlib
import lzma
import typing
import numpy as np

from ._encoders import Encoder

try:
    import lz4.block  # type: ignore[import]

    _HAVE_LZ4 = True
except ImportError:
    _HAVE_LZ4 = False


class Compressor(typing.Protocol):
    def get_decompressed_data(self, data: bytes, encoder: Encoder) -> bytes:
        ...


class NoCompressor:
    def __init__(self, header_type: np.dtype) -> None:
        self._header_type = header_type

    def get_decompressed_data(self, data: bytes, encoder: Encoder) -> bytes:
        decoded = encoder.decode(data)
        num_header_bytes = int(self._header_type.itemsize)
        num_decoded_bytes = int(np.frombuffer(decoded[:num_header_bytes], self._header_type)[0])

        if len(decoded) == num_header_bytes:
            # header was encoded separately, decode the data...
            header_offset = len(encoder.encode(decoded))
            decoded_data = encoder.decode(data[header_offset:])
            return decoded_data[:num_decoded_bytes]
        return decoded[num_header_bytes : num_header_bytes + num_decoded_bytes]


class CompressorBase(abc.ABC):
    def __init__(self, header_type: np.dtype) -> None:
        self._header_type = header_type

    def get_decompressed_data(self, data: bytes, encoder: Encoder) -> bytes:
        header, data_offset = self._read_header(data, encoder)
        raw_block_size = int(header[1])
        block_sizes = header[3:]

        encoded_data_bytes = encoder.encoded_bytes(int(sum(s for s in block_sizes)))
        return self._uncompress_blocks(
            decoded_data=encoder.decode(data[data_offset : data_offset + encoded_data_bytes]),
            block_sizes=block_sizes,
            raw_block_size=raw_block_size,
        )

    def _read_header(self, data: bytes, encoder: Encoder) -> typing.Tuple[np.ndarray, int]:
        decoded_header_bytes = int(self._header_type.itemsize) * 3
        encoded_header_bytes = encoder.encoded_bytes(decoded_header_bytes)
        header = np.frombuffer(
            encoder.decode(data[:encoded_header_bytes])[:decoded_header_bytes], dtype=self._header_type
        )

        num_blocks = int(header[0])
        decoded_block_sizes_bytes = num_blocks * int(self._header_type.itemsize)
        encoded_block_sizes_bytes = encoder.encoded_bytes(decoded_block_sizes_bytes)
        return (
            np.concatenate(
                [
                    header,
                    np.frombuffer(
                        encoder.decode(data[encoded_header_bytes : encoded_header_bytes + encoded_block_sizes_bytes])[
                            :encoded_block_sizes_bytes
                        ],
                        dtype=self._header_type,
                    ),
                ]
            ),
            encoded_header_bytes + encoded_block_sizes_bytes,
        )

    def _uncompress_blocks(self, decoded_data: bytes, block_sizes: np.ndarray, raw_block_size: int) -> bytes:
        block_offsets = np.array([0] + [int(s) for s in np.cumsum(block_sizes)], dtype=self._header_type)
        return np.concatenate(
            [
                np.frombuffer(
                    self._decompress(decoded_data[block_offsets[i] : block_offsets[i + 1]], raw_block_size),
                    dtype=np.byte,
                )
                for i in range(len(block_sizes))
            ]
        ).tobytes()

    @abc.abstractmethod
    def _decompress(self, data: bytes, uncompressed_size: int) -> bytes:
        ...


class ZLIBCompressor(CompressorBase):
    def __init__(self, header_type: np.dtype) -> None:
        super().__init__(header_type)

    def _decompress(self, data: bytes, uncompressed_size: int) -> bytes:
        return zlib.decompress(data)


class LZMACompressor(CompressorBase):
    def __init__(self, header_type: np.dtype) -> None:
        super().__init__(header_type)

    def _decompress(self, data: bytes, uncompressed_size: int) -> bytes:
        return lzma.decompress(data)


class LZ4Compressor(CompressorBase):
    def __init__(self, header_type: np.dtype) -> None:
        assert _HAVE_LZ4 and "LZ4 module required for uncompression"
        super().__init__(header_type)

    def _decompress(self, data: bytes, uncompressed_size: int) -> bytes:
        return lz4.block.decompress(data, uncompressed_size=uncompressed_size)
