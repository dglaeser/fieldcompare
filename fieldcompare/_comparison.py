"""Class to store information on a comparison"""

from typing import Optional, List
from dataclasses import dataclass
from enum import Enum, auto


class Status(Enum):
    passed = auto()
    failed = auto()
    skipped = auto()
    error = auto()

    def __bool__(self) -> bool:
        return self != Status.failed and self != Status.error


@dataclass
class Comparison:
    name: str
    status: Status
    stdout: str
    cpu_time: Optional[float] = None

    def __bool__(self) -> bool:
        return bool(self.status)


class ComparisonSuite:
    def __init__(self,
                 status: Optional[Status] = None,
                 error_log: str = "",
                 error_shortlog: str = "") -> None:
        self._comparisons: List[Comparison] = []
        self._status = status
        self._error_log = error_log
        self._error_shortlog = error_shortlog

    def __iter__(self):
        return iter(self._comparisons)

    def __bool__(self) -> bool:
        if self._status is not None:
            return bool(self._status)
        return all(comp for comp in self._comparisons)

    def insert(self, comp: Comparison) -> None:
        self._comparisons.append(comp)

    @property
    def status(self) -> Status:
        if self._status is not None:
            return self._status
        elif any(comp.status == Status.error for comp in self._comparisons):
            return Status.error
        elif any(not comp for comp in self._comparisons):
            return Status.failed
        else:
            return Status.passed

    @status.setter
    def status(self, status: Status) -> None:
        self._status = status

    @property
    def size(self) -> int:
        return len(self._comparisons)

    @property
    def error_log(self) -> str:
        assert not self._error_log or self.status != Status.passed
        return self._error_log

    @property
    def error_shortlog(self) -> str:
        assert not self._error_shortlog or self.status != Status.passed
        return self._error_shortlog
