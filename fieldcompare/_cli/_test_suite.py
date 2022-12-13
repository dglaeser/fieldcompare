"""Data classes to hold the results of a CLI run"""

from __future__ import annotations
from typing import Optional, List, Iterator
from dataclasses import dataclass
from enum import Enum, auto

from .._field_data_comparison import FieldComparisonStatus


class TestResult(Enum):
    passed = auto()
    failed = auto()
    error = auto()
    skipped = auto()

    def __bool__(self) -> bool:
        return self not in [TestResult.failed, TestResult.error]


@dataclass
class Test:
    name: str
    result: TestResult
    shortlog: str
    stdout: str
    cpu_time: Optional[float]


class TestSuite:
    def __init__(self,
                 tests: List[Test],
                 name: Optional[str] = None,
                 result: Optional[TestResult] = None,
                 shortlog: str = "",
                 stdout: str = "",
                 cpu_time: Optional[float] = None) -> None:
        self._tests = tests
        self._name = name
        self._result = result
        self._shortlog = shortlog
        self._stdout = stdout
        self._cpu_time = cpu_time

    def __bool__(self) -> bool:
        def _is_true(result: TestResult) -> bool:
            return result not in [TestResult.failed, TestResult.error]

        if self._result is not None:
            return _is_true(self._result)
        return all(_is_true(t.result) for t in self._tests)

    def __iter__(self) -> Iterator[Test]:
        return iter(self._tests)

    @property
    def name(self) -> str:
        if self._name is None:
            return "n/a"
        return self._name

    @property
    def num_tests(self) -> int:
        return len(self._tests)

    @property
    def result(self) -> TestResult:
        if self._result is not None:
            return self._result
        return TestResult.passed if self else TestResult.failed

    @property
    def shortlog(self) -> str:
        return self._shortlog

    @property
    def stdout(self) -> str:
        return self._stdout

    @property
    def cpu_time(self) -> Optional[float]:
        return self._cpu_time

    def with_overridden(self,
                        cpu_time: Optional[float] = None,
                        name: Optional[str] = None,
                        result: Optional[TestResult] = None,
                        shortlog: Optional[str] = None) -> TestSuite:
        return TestSuite(
            tests=self._tests,
            name=(name if name is not None else self._name),
            result=(result if result is not None else self._result),
            shortlog=(shortlog if shortlog is not None else self._shortlog),
            stdout=self._stdout,
            cpu_time=(cpu_time if cpu_time is not None else self._cpu_time)
        )


def to_test_result(status: FieldComparisonStatus) -> TestResult:
    if status.passed:
        return TestResult.passed
    if status.failed:
        return TestResult.failed
    if status.error:
        return TestResult.error
    return TestResult.skipped
