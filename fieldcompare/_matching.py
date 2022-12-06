"""Functions for detecting matching strings in two given iterables"""

from typing import List, Tuple, Iterable, Protocol
from dataclasses import dataclass
from os.path import join, relpath
from os import walk


class _Named(Protocol):
    @property
    def name(self) -> str:
        ...


@dataclass
class MatchResult:
    """Data class to store the result of finding matching strings"""
    matches: List[str]
    orphans: Tuple[List[str], List[str]]

    def __iter__(self):
        return iter(self.matches)


def find_matches(names: List[str], reference_names: List[str]) -> MatchResult:
    """Finds matching and non-matching strings in the two given iterables"""
    names_set = set(names)
    reference_names_set = set(reference_names)
    res_orphans = list(names_set.difference(reference_names_set))
    ref_orphans = list(reference_names_set.difference(names_set))
    matches = list(names_set.intersection(reference_names_set))
    return MatchResult(matches, (res_orphans, ref_orphans))


def find_matching_names(names: Iterable[_Named], references: Iterable[_Named]) -> MatchResult:
    """Looks for matching names in the provided objects exposing a name"""
    return find_matches(
        list(map(lambda v: v.name, names)),
        list(map(lambda v: v.name, references))
    )


def find_matching_file_names(folder: str, reference_folder: str) -> MatchResult:
    """Looks for matching supported files in a results & reference folder to be compared"""
    return find_matches(
        _find_sub_files_recursively(folder),
        _find_sub_files_recursively(reference_folder)
    )


def _find_sub_files_recursively(folder) -> List[str]:
    result: list = []
    for root, _, files in walk(folder):
        result.extend(relpath(join(root, filename), folder) for filename in files)
    return result
