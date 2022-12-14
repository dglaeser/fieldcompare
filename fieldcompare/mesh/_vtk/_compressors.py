import abc
import zlib
import lzma
import typing
import numpy as np

from ._decoders import Decoder

try:
    import lz4.block  # type: ignore[import]
    _HAVE_LZ4 = True
except ImportError:
    _HAVE_LZ4 = False


class Compressor(typing.Protocol):
    def get_decompressed_data(self, data: bytes, decoder: Decoder) -> bytes:
        ...


class NoCompressor:
    def __init__(self, header_type: np.dtype) -> None:
        self._header_type = header_type

    def get_decompressed_data(self, data: bytes, decoder: Decoder) -> bytes:
        header_size = int(self._header_type.itemsize)
        encoded_header_size = decoder.encoded_size(header_size)
        decoded_header = decoder.decode(data[:encoded_header_size])
        num_decoded_bytes = int(np.frombuffer(decoded_header[:header_size], self._header_type)[0])
        num_encoded_bytes = encoded_header_size + decoder.encoded_size(num_decoded_bytes)
        decoded = decoder.decode(data[encoded_header_size:num_encoded_bytes])
        if num_decoded_bytes > len(decoded):
            # in this case the header and data were maybe decoded together
            num_encoded_bytes = decoder.encoded_size(header_size + num_decoded_bytes)
            decoded = decoder.decode(data[:num_encoded_bytes])
            assert len(decoded[header_size:]) == num_decoded_bytes
            return decoded[header_size:]
        return decoded[:num_decoded_bytes]


class CompressorBase(abc.ABC):
    def __init__(self, header_type: np.dtype) -> None:
        self._header_type = header_type
        self._header_size = int(self._header_type.itemsize)*3

    def get_decompressed_data(self, data: bytes, decoder: Decoder) -> bytes:
        header = self._read_header(data, decoder)
        num_blocks = int(header[0])
        raw_block_size = int(header[1])
        block_sizes = self._read_block_sizes(data, decoder, num_blocks)
        return self._uncompress_blocks(data, decoder, block_sizes, raw_block_size)

    def _read_header(self, data: bytes, decoder: Decoder) -> np.ndarray:
        decoded = decoder.decode(data[:decoder.encoded_size(self._header_size)])
        return np.frombuffer(decoded[:self._header_size], self._header_type)

    def _read_block_sizes(self, data: bytes, decoder: Decoder, num_blocks: int) -> np.ndarray:
        decoded_size = self._decoded_header_size_with_blocks(num_blocks)
        encoded_size = decoder.encoded_size(decoded_size)
        decoded = decoder.decode(data[:encoded_size])
        return np.frombuffer(decoded[:decoded_size], self._header_type)[3:]

    def _uncompress_blocks(self,
                           data: bytes,
                           decoder: Decoder,
                           block_sizes: np.ndarray,
                           raw_block_size: int) -> bytes:
        decoded_block_offsets = np.array(
            [0] + [s for s in np.cumsum(block_sizes)],
            dtype=self._header_type
        )

        encoded_data_offset = decoder.encoded_size(
            self._decoded_header_size_with_blocks(len(block_sizes))
        )
        encoded_data_size = decoder.encoded_size(decoded_block_offsets[-1])
        decoded_data = decoder.decode(data[
            encoded_data_offset:
            encoded_data_offset + encoded_data_size
        ])

        decompressed = self._decompress(
            decoded_data[decoded_block_offsets[0]:decoded_block_offsets[1]],
            raw_block_size
        )
        for i in range(1, len(block_sizes)):
            decompressed += self._decompress(
                decoded_data[decoded_block_offsets[i]:decoded_block_offsets[i+1]],
                raw_block_size
            )
        return decompressed

    def _decoded_header_size_with_blocks(self, num_blocks: int) -> int:
        return self._header_size + int(self._header_type.itemsize)*num_blocks

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
