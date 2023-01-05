"""Functions for detecting matching strings in two given iterables"""

from typing import List, Tuple, Iterable, Protocol, TypeVar, Callable, Any
from dataclasses import dataclass
from os.path import join, relpath
from os import walk


class _Named(Protocol):
    @property
    def name(self) -> str:
        ...


@dataclass
class MatchResult:
    """Data class to store the result of finding matches in two ranges"""

    matches: List[Tuple[Any, Any]]
    orphans_in_source: List[Any]
    orphans_in_reference: List[Any]


T1 = TypeVar("T1")
T2 = TypeVar("T2")


def find_matches(
    source: Iterable[T1], reference: Iterable[T2], eq_predicate: Callable[[T1, T2], bool] = lambda a, b: a == b
) -> MatchResult:
    """Find matches and orphans in the two ranges using the given equality predicate"""
    matches = []
    orphans_source = []
    orphans_target = list(v for v in reference)

    def _find_and_add(s) -> bool:
        for t in orphans_target:
            if eq_predicate(s, t):
                matches.append((s, t))
                orphans_target.remove(t)
                return True
        return False

    for s in source:
        if not _find_and_add(s):
            orphans_source.append(s)

    return MatchResult(matches, orphans_source, orphans_target)


def find_matches_by_name(first: Iterable[_Named], second: Iterable[_Named]) -> MatchResult:
    """Looks for matching names in the provided objects exposing a name"""
    return find_matches(first, second, lambda a, b: a.name == b.name)


def find_matching_file_names(folder: str, reference_folder: str) -> MatchResult:
    """Looks for matching supported files in a results & reference folder to be compared"""
    return find_matches(_find_sub_files_recursively(folder), _find_sub_files_recursively(reference_folder))


def _find_sub_files_recursively(folder) -> List[str]:
    result: list = []
    for root, _, files in walk(folder):
        result.extend(relpath(join(root, filename), folder) for filename in files)
    return result
