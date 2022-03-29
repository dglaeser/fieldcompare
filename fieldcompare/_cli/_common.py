"""Common functions used in the command-line interface"""

from typing import List, Dict, Optional, Tuple, Sequence
from textwrap import indent
from re import compile

from .._common import _default_base_tolerance
from ..colors import make_colored, TextColor
from ..logging import Logger, ModifiedVerbosityLoggerFacade, IndentedLoggingFacade
from ..field_io import read_fields


class InclusionFilter:
    def __init__(self, regexes: Optional[List[str]] = None) -> None:
        self._regexes = regexes

    def __call__(self, names: Sequence[str]) -> List[str]:
        if not self._regexes:
            return list(names)

        result = []
        for regex in self._regexes:
            # support unix bash wildcard patterns
            if regex.startswith("*") or regex.startswith("?"):
                regex = f".{regex}"
            pattern = compile(regex)
            result.extend(list(filter(lambda n: pattern.match(n), names)))
        return list(set(result))


class ExclusionFilter:
    def __init__(self, regexes: Optional[List[str]] = None) -> None:
        self._regexes = regexes

    def __call__(self, names: Sequence[str]) -> List[str]:
        if not self._regexes:
            return list(names)

        matches = InclusionFilter(self._regexes)(names)
        return list(set(names).difference(set(matches)))


class FieldToleranceMap:
    def __init__(self,
                 default_tolerance: float = _default_base_tolerance(),
                 tolerances: Dict[str, float] = {}) -> None:
        self._default_tolerance = default_tolerance
        self._field_tolerances = tolerances

    def get(self, field_name: str) -> float:
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


def _read_fields_from_file(filename: str, logger: Logger):
    logger.log(f"Reading fields from '{filename}'\n", verbosity_level=1)
    low_verbosity_logger = ModifiedVerbosityLoggerFacade(logger, verbosity_change=-2)
    file_io_logger = IndentedLoggingFacade(low_verbosity_logger, " "*4)
    return read_fields(filename, logger=file_io_logger)


def _get_status_string(passed: bool) -> str:
    if passed:
        return make_colored("PASSED", color=TextColor.green)
    return make_colored("FAILED", color=TextColor.red)


def _style_as_warning(text: str) -> str:
    return make_colored(text, color=TextColor.yellow)


def _style_as_error(text: str) -> str:
    return make_colored(text, color=TextColor.red)


def _make_list_string(missing_fields: List[str]) -> str:
    return indent("\n".join(missing_fields), "- ")


def _bool_to_exit_code(value: bool) -> int:
    return int(not value)
