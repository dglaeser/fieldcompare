"""Logger for output during CLI runs"""

from __future__ import annotations
from typing import TextIO
from textwrap import indent
import sys


class CLILogger:
    def __init__(self,
                 verbosity_level: int = 1,
                 output_stream: TextIO = sys.stdout,
                 line_prefix: str = "") -> None:
        self._verbosity = verbosity_level
        self._output_stream = output_stream
        self._line_prefix = line_prefix

    @property
    def verbosity_level(self) -> int:
        return self._verbosity

    def log(self, message: str, verbosity_level: int = 1) -> None:
        if self._verbosity > 0 and self._verbosity >= verbosity_level:
            self._output_stream.write(indent(message, self._line_prefix))

    def with_verbosity(self, verbosity_level: int) -> CLILogger:
        return CLILogger(
            verbosity_level=verbosity_level,
            output_stream=self._output_stream,
            line_prefix=self._line_prefix
        )

    def with_modified_verbosity(self, verbosity_change: int) -> CLILogger:
        return CLILogger(
            verbosity_level=self._verbosity + verbosity_change,
            output_stream=self._output_stream,
            line_prefix=self._line_prefix
        )

    def with_prefix(self, prefix: str) -> CLILogger:
        return CLILogger(
            verbosity_level=self._verbosity,
            output_stream=self._output_stream,
            line_prefix=prefix
        )
