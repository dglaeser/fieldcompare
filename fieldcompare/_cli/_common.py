"""Common functionality used in the command-line interface"""

from typing import List, Dict, Tuple, Optional, Union
from fnmatch import fnmatch

from ..protocols import DynamicTolerance
from ..predicates import ScaledTolerance

from .._format import as_success, as_error, as_warning, highlighted
from ._logger import CLILogger
from ._test_suite import TestStatus


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
    def __init__(
        self,
        tolerances: Dict[str, Union[float, DynamicTolerance]] = {},
        default_tol: Optional[Union[float, DynamicTolerance]] = None,
    ) -> None:
        self._field_tolerances = tolerances
        self._default = default_tol

    def __call__(self, field_name: str) -> Optional[Union[float, DynamicTolerance]]:
        tol = self._field_tolerances.get(field_name)
        return tol if tol is not None else self._default


def _parse_field_tolerances(
    tolerance_strings: Optional[List[str]] = None,
    allow_dynamic_tolerances: bool = False,
) -> FieldToleranceMap:
    def _is_field_tolerance_string(tol_string: str) -> bool:
        return ":" in tol_string

    def _get_field_name_tolerance_str_pair(tol_string: str) -> Tuple[str, str]:
        name, tol_string = tol_string.split(":")
        return name, tol_string

    def _make_tolerance(tol_string: str) -> Union[float, DynamicTolerance]:
        if allow_dynamic_tolerances and tol_string.endswith("*max"):
            return ScaledTolerance(base_tolerance=float(tol_string.rsplit("*max")[0]))
        return float(tol_string)

    if tolerance_strings is not None:
        field_tols = {}
        default_tol: Optional[Union[float, DynamicTolerance]] = None
        for tol_string in tolerance_strings:
            if _is_field_tolerance_string(tol_string):
                name, value_str = _get_field_name_tolerance_str_pair(tol_string)
                field_tols[name] = _make_tolerance(value_str)
            else:
                default_tol = _make_tolerance(tol_string)
        return FieldToleranceMap(field_tols, default_tol=default_tol)
    return FieldToleranceMap()


class FileTypeMap:
    def __init__(self, mapping: List[Tuple[str, PatternFilter]] = []) -> None:
        self._mapping = mapping

    def __call__(self, filename: str):
        for file_type, regex in self._mapping:
            if regex(filename):
                return file_type
        return None


def _make_file_type_map(map_args: Optional[List[str]]) -> FileTypeMap:
    if map_args is None:
        return FileTypeMap()

    file_types: List[str] = []
    regexes: List[List[str]] = []
    for mapping in map_args:
        if ":" not in mapping:
            raise IOError(f"Missing colon in mapping {mapping}. Reader mappings take the form 'READER:REGEX'.")
        file_type, regex = mapping.split(":", maxsplit=1)
        if not any(_t == file_type for _t in file_types):
            file_types.append(file_type)
            regexes.append([regex])
        else:
            regexes[file_types.index(file_type)].append(regex)
    return FileTypeMap(mapping=[(file_type, PatternFilter(rx)) for file_type, rx in zip(file_types, regexes)])


def _bool_to_exit_code(value: bool) -> int:
    return int(not value)


def _log_suite_summary(suite, comparison_type: str, logger: CLILogger) -> None:
    def _counted(count: int) -> str:
        return f"{count} {comparison_type} {_plural('comparison', count)}"

    def _padded(label: str) -> str:
        return f"{label: ^9}"

    def _log_line(label: str, report: str, verbosity_level: int = 1) -> None:
        logger.log(f"[{label}] {report}\n", verbosity_level=verbosity_level)

    passed = [t for t in suite if t.status == TestStatus.passed]
    skipped = [t for t in suite if t.status == TestStatus.skipped]
    failed = [t for t in suite if t.status in [TestStatus.failed, TestStatus.error]]

    num_comparisons = len(passed) + len(failed)
    _log_line(highlighted(_padded("=" * 7)), f"{_counted(num_comparisons)} performed")

    if passed:
        _log_line(as_success(_padded("PASSED")), _counted(len(passed)))

    if skipped:
        _log_line(as_warning(_padded("SKIPPED")), _counted(len(skipped)))
        for test in skipped:
            _log_line(as_warning(_padded("SKIPPED")), f"{highlighted(test.name)}: ({test.shortlog})", verbosity_level=3)

    if failed:
        _log_line(as_error(_padded("FAILED")), f"{_counted(len(failed))}, listed below:")
        for test in failed:
            _log_line(as_error(_padded("FAILED")), f"{highlighted(test.name)}: ({test.shortlog})")


def _plural(word: str, count: int) -> str:
    return f"{word}s" if count != 1 else word
