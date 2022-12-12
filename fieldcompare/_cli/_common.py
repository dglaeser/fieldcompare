"""Common functionality used in the command-line interface"""

from typing import List, Dict, Tuple, Optional
from fnmatch import fnmatch

from .._common import _default_base_tolerance
from .._format import (
    as_success,
    as_error,
    as_warning,
    highlighted
)

from ._logger import CLILogger
from ._test_suite import TestSuite, TestResult


class PatternFilter:
    """Predicate that returns true if a string matches any of the given patterns."""
    def __init__(self, patterns: List[str]) -> None:
        self._patterns = patterns

    def __call__(self, name: str) -> bool:
        return any(fnmatch(name, pattern) for pattern in self._patterns)


def _include_all() -> PatternFilter:
    return PatternFilter(["*"])


def _exclude_all() -> PatternFilter:
    return PatternFilter([])


class FieldToleranceMap:
    def __init__(self,
                 default_tolerance: float = _default_base_tolerance(),
                 tolerances: Dict[str, float] = {}) -> None:
        self._default_tolerance = default_tolerance
        self._field_tolerances = tolerances

    def __call__(self, field_name: str) -> float:
        return self._field_tolerances.get(field_name, self._default_tolerance)


def _parse_field_tolerances(tolerance_strings: Optional[List[str]] = None) -> FieldToleranceMap:
    def _is_field_tolerance_string(tol_string: str) -> bool:
        return ":" in tol_string

    def _get_field_name_tolerance_value_pair(tol_string: str) -> Tuple[str, float]:
        name, tol_string = tol_string.split(":")
        return name, float(tol_string)

    if tolerance_strings is not None:
        default_tol = _default_base_tolerance()
        field_tols = {}
        for tol_string in tolerance_strings:
            if _is_field_tolerance_string(tol_string):
                name, value = _get_field_name_tolerance_value_pair(tol_string)
                field_tols[name] = value
            else:
                default_tol = float(tol_string)
        return FieldToleranceMap(default_tol, field_tols)
    return FieldToleranceMap()


def _bool_to_exit_code(value: bool) -> int:
    return int(not value)


def _log_suite_summary(suite,
                       comparison_type: str,
                       logger: CLILogger) -> None:
    def _counted(count: int) -> str:
        return f"{count} {comparison_type} {_plural('comparison', count)}"

    def _padded(label: str) -> str:
        return f"{label: ^9}"

    def _log_line(label: str, report: str, verbosity_level: int = 1) -> None:
        logger.log(f"[{label}] {report}\n", verbosity_level=verbosity_level)

    passed = [t for t in suite if t.result == TestResult.passed]
    skipped = [t for t in suite if t.result == TestResult.skipped]
    failed = [t for t in suite if t.result in [TestResult.failed, TestResult.error]]

    num_comparisons = len(passed) + len(failed)
    _log_line(highlighted(_padded("="*7)), f"{_counted(num_comparisons)} performed")

    if passed:
        _log_line(as_success(_padded("PASSED")), _counted(len(passed)))

    if skipped:
        _log_line(as_warning(_padded("SKIPPED")), _counted(len(skipped)))
        for test in skipped:
            _log_line(
                as_warning(_padded("SKIPPED")),
                f"{highlighted(test.name)}: ({test.shortlog})",
                verbosity_level=2
            )

    if failed:
        _log_line(as_error(_padded("FAILED")), f"{_counted(len(failed))}, listed below:")
        for test in failed:
            _log_line(
                as_error(_padded("FAILED")),
                f"{highlighted(test.name)}: ({test.shortlog})"
            )


def _plural(word: str, count: int) -> str:
    return f"{word}s" if count != 1 else word
