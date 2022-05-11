"""Interface & implementations for loggers"""

import sys
from typing import TextIO, Optional, Protocol


class Logger(Protocol):
    """Interface for loggers"""
    @property
    def verbosity_level(self) -> int:
        ...

    @verbosity_level.setter
    def verbosity_level(self, level: int) -> None:
        ...

    def log(self, message: str, verbosity_level: Optional[int] = None) -> None:
        ...


class LoggerBase:
    """Interface for loggers"""
    def __init__(self, verbosity_level: Optional[int] = None) -> None:
        self._verbosity_level = verbosity_level

    @property
    def verbosity_level(self) -> Optional[int]:
        return self._verbosity_level

    @verbosity_level.setter
    def verbosity_level(self, level: int) -> None:
        self._verbosity_level = level

    def log(self, message: str, verbosity_level: Optional[int] = None) -> None:
        if self._verbosity_level is None:
            self._log(message)
        elif verbosity_level is None and self._verbosity_level > 0:
            self._log(message)
        elif verbosity_level is not None and verbosity_level <= self._verbosity_level:
            self._log(message)

    def _log(self, message: str) -> None:
        """Implementation-defined message logging"""


class Loggable(Protocol):
    """Interface for classes that allow attaching a logger."""
    def attach_logger(self, logger: Logger) -> None:
        ...


class StreamLogger(LoggerBase):
    """Logging into output streams"""
    def __init__(self,
                 ostream: TextIO,
                 verbosity_level: Optional[int] = None) -> None:
        self._ostream = ostream
        super().__init__(verbosity_level)

    def _log(self, message: str) -> None:
        self._ostream.write(message)


class StandardOutputLogger(StreamLogger):
    """Logging to standard out"""
    def __init__(self, verbosity_level: Optional[int] = None) -> None:
        super().__init__(sys.stdout, verbosity_level)


class NullDeviceLogger(LoggerBase):
    """Logger interface that does no logging"""
    def __init__(self, verbosity_level: Optional[int] = None) -> None:
        super().__init__(verbosity_level)

    def _log(self, message: str) -> None:
        pass


class ModifiedVerbosityLoggerFacade(LoggerBase):
    """Wrapper around a logger to write to it with modified verbosity"""
    def __init__(self, logger: Logger, verbosity_change: int) -> None:
        self._logger = logger
        self._verbosity_change = verbosity_change
        super().__init__(logger.verbosity_level)
        if logger.verbosity_level:
            self.verbosity_level = logger.verbosity_level + verbosity_change

    def _log(self, message: str) -> None:
        self._logger.log(message)


class IndentedLoggingFacade(LoggerBase):
    """Wrapper around a logger to write indented (useful for logging of sub-routines)"""
    def __init__(self, logger: Logger, first_line_prefix: str) -> None:
        self._logger = logger
        self._first_line_prefix = first_line_prefix
        super().__init__(logger.verbosity_level)

    def _log(self, message: str) -> None:
        self._logger.log(self._indent(message))

    def _indent(self, message: str) -> str:
        if not message:
            return message

        lines = message.split("\n")
        last_is_empty = not lines[-1]
        lines[0] = self._first_line_prefix + lines[0]
        if len(lines) > 1:
            indentation = " "*len(self._first_line_prefix)
            lines[1:-1] = [indentation + line for line in lines[1:-1]]
            if not last_is_empty:
                lines[-1] = indentation + lines[-1]
        return "\n".join(lines)
