"""Interface & implementations for loggers"""

import sys
from typing import TextIO, Protocol, List


class Logger(Protocol):
    """Interface for loggers"""
    @property
    def verbosity_level(self) -> int:
        ...

    @verbosity_level.setter
    def verbosity_level(self, level: int) -> None:
        ...

    def log(self, message: str, verbosity_level: int = 1) -> None:
        ...


class LoggerBase:
    """Interface for loggers"""
    def __init__(self, verbosity_level: int = 100) -> None:
        self._verbosity_level = verbosity_level

    @property
    def verbosity_level(self) -> int:
        return self._verbosity_level

    @verbosity_level.setter
    def verbosity_level(self, level: int) -> None:
        self._verbosity_level = level

    def log(self, message: str, verbosity_level: int = 1) -> None:
        if verbosity_level <= self._verbosity_level:
            self._log(message)

    def _log(self, message: str) -> None:
        """Implementation-defined message logging"""


class Loggable(Protocol):
    """Interface for classes that allow attaching a logger."""
    def attach_logger(self, logger: Logger) -> None:
        ...

    def remove_logger(self, logger: Logger) -> None:
        ...


class LoggableBase:
    """Base class for classes that do logging"""
    def __init__(self) -> None:
        self._loggers: List[Logger] = []

    def attach_logger(self, logger: Logger) -> None:
        if not any(_logger is logger for _logger in self._loggers):
            self._loggers.append(logger)

    def remove_logger(self, logger: Logger) -> None:
        for _logger in self._loggers:
            if _logger is logger:
                self._loggers.remove(_logger)

    def _log(self, message: str, verbosity_level: int = 1) -> None:
        for _logger in self._loggers:
            _logger.log(message, verbosity_level)


class StreamLogger(LoggerBase):
    """Logging into output streams"""
    def __init__(self,
                 ostream: TextIO,
                 verbosity_level: int = 100) -> None:
        self._ostream = ostream
        super().__init__(verbosity_level)

    def _log(self, message: str) -> None:
        self._ostream.write(message)


class StandardOutputLogger(StreamLogger):
    """Logging to standard out"""
    def __init__(self, verbosity_level: int = 100) -> None:
        super().__init__(sys.stdout, verbosity_level)


class NullDeviceLogger(LoggerBase):
    """Logger interface that does no logging"""
    def __init__(self, verbosity_level: int = 100) -> None:
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
