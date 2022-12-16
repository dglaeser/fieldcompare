from typing import Optional, Tuple

from ._encoders import Encoder, NoEncoder, Base64Encoder


class VTKXMLAppendix:
    def __init__(self, content: bytes) -> None:
        self._content = None
        app_positions = _find_appendix_positions(content)
        if app_positions is not None:
            begin_pos, end_pos = app_positions
            self._encoding = self._determine_encoding(content[begin_pos-100:])
            self._content = content[begin_pos:end_pos]

    @property
    def is_empty(self) -> bool:
        return self._content is None

    @property
    def encoder(self) -> Encoder:
        if self._encoding == "base64":
            return Base64Encoder()
        if self._encoding == "raw":
            return NoEncoder()
        raise NotImplementedError(f"Unupported encoding '{self._encoding}'")

    def get(self, offset: int = 0) -> bytes:
        assert self._content is not None
        return self._content[offset:]

    def _determine_encoding(self, content: bytes) -> str:
        pos = content.rfind(b"<AppendedData")
        pos = content.find(b"encoding", pos)
        encoding_range = _find_enclosed_content_range(content, pos, b'"', b'"')
        assert encoding_range is not None
        return str(content[encoding_range[0]:encoding_range[1]].decode("ascii"))


def _find_appendix_positions(content: bytes) -> Optional[Tuple[int, int]]:
    start_pos = content.find(b"<AppendedData")
    if _is_end(start_pos):
        return None
    position = _find_enclosed_content_range(content, start_pos, b"<", b">")
    if position is None:
        return None
    app_begin_pos = content.find(b"_", position[1] + len(b">"))
    if _is_end(app_begin_pos):
        return None
    app_end_pos = content.find(b"</AppendedData>")
    if _is_end(app_end_pos):
        return None
    return app_begin_pos + len(b"_"), app_end_pos


def _find_enclosed_content_range(content: bytes,
                                 start_pos: int,
                                 open_char: bytes,
                                 close_char: bytes) -> Optional[Tuple[int, int]]:
    cur_pos = content.find(open_char, start_pos)
    start_pos = cur_pos + 1
    if _is_end(cur_pos):
        return None

    if open_char == close_char:
        end_pos = content.find(close_char, start_pos)
        return None if end_pos is None else (start_pos, end_pos)

    open_count = 1
    close_count = 0

    while not _is_end(cur_pos):
        next_open_pos = content.find(open_char, cur_pos + 1)
        next_close_pos = content.find(close_char, cur_pos + 1)
        if not _is_end(next_close_pos):
            close_count += 1
            if open_count == close_count and (_is_end(next_open_pos) or next_close_pos < next_open_pos):
                return start_pos, next_close_pos
            elif not _is_end(next_open_pos):
                open_count += 1
        cur_pos = max(next_open_pos, next_close_pos)
    return None


def _is_end(position: int) -> bool:
    return position == -1
