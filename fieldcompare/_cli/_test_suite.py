# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Data classes to hold the results of a CLI run"""

from __future__ import annotations
from typing import Iterator
from dataclasses import dataclass
from enum import Enum, auto


class TestStatus(Enum):
    passed = auto()
    failed = auto()
    error = auto()
    skipped = auto()

    def __bool__(self) -> bool:
        return self not in [TestStatus.failed, TestStatus.error]

    def __str__(self) -> str:
        names = {
            TestStatus.passed: "PASSED",
            TestStatus.failed: "FAILED",
            TestStatus.error: "FAILED",
            TestStatus.skipped: "SKIPPED",
        }
        return names[self]


@dataclass
class TestResult:
    name: str
    status: TestStatus
    shortlog: str
    stdout: str
    cpu_time: float | None


class TestSuite:
    def __init__(  # noqa: PLR0913
        self,
        tests: list[TestResult],
        name: str | None = None,
        status: TestStatus | None = None,
        shortlog: str = "",
        stdout: str = "",
        cpu_time: float | None = None,
    ) -> None:
        self._tests = tests
        self._name = name
        self._status = status
        self._shortlog = shortlog
        self._stdout = stdout
        self._cpu_time = cpu_time

    def __bool__(self) -> bool:
        def _is_true(result: TestStatus) -> bool:
            return result not in [TestStatus.failed, TestStatus.error]

        if self._status is not None:
            return _is_true(self._status)
        return all(_is_true(t.status) for t in self._tests)

    def __iter__(self) -> Iterator[TestResult]:
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
    def status(self) -> TestStatus:
        if self._status is not None:
            return self._status
        return TestStatus.passed if self else TestStatus.failed

    @property
    def shortlog(self) -> str:
        return self._shortlog

    @property
    def stdout(self) -> str:
        return self._stdout

    @property
    def cpu_time(self) -> float | None:
        return self._cpu_time

    def with_overridden(
        self,
        cpu_time: float | None = None,
        name: str | None = None,
        status: TestStatus | None = None,
        shortlog: str | None = None,
    ) -> TestSuite:
        return TestSuite(
            tests=self._tests,
            name=(name if name is not None else self._name),
            status=(status if status is not None else self._status),
            shortlog=(shortlog if shortlog is not None else self._shortlog),
            stdout=self._stdout,
            cpu_time=(cpu_time if cpu_time is not None else self._cpu_time),
        )
