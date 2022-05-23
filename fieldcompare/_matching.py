"""Functions for automatic selection of files and fields to be compared"""

from dataclasses import dataclass
from typing import List, Iterable
from os.path import join, relpath
from os import walk

from ._field import FieldInterface

@dataclass
class MatchResult:
    """Data class to store the result of finding matching fields/files"""
    matches: List[str]
    orphan_results: List[str]
    orphan_references: List[str]


def find_matching_names(result_names: Iterable[str],
                        reference_names: Iterable[str]) -> MatchResult:
    res_orphans = list(set(result_names).difference(reference_names))
    ref_orphans = list(set(reference_names).difference(result_names))
    matches = list(set(result_names).intersection(reference_names))
    return MatchResult(matches, res_orphans, ref_orphans)


def find_matching_field_names(result_fields: Iterable[FieldInterface],
                              reference_fields: Iterable[FieldInterface]) -> MatchResult:
    """Looks for matching field names in the provided results & reference fields"""
    return find_matching_names(
        [f.name for f in result_fields],
        [f.name for f in reference_fields]
    )


def find_matching_file_names(results_folder: str,
                             references_folder: str) -> MatchResult:
    """Looks for matching supported files in a results & reference folder to be compared"""
    return find_matching_names(
        _find_sub_files_recursively(results_folder),
        _find_sub_files_recursively(references_folder)
    )


def _find_sub_files_recursively(folder) -> List[str]:
    result: list = []
    for root, _, files in walk(folder):
        result.extend(relpath(join(root, filename), folder) for filename in files)
    return result
