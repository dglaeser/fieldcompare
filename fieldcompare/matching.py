"""Functions for automatic selection of files and fields to be compared"""

from dataclasses import dataclass
from typing import List, Iterable
from os.path import join, relpath
from os import walk

from .field import Field

@dataclass
class MatchResult:
    """Data class to store the result of finding matching fields/files"""
    matches: List[str]
    orphan_results: List[str]
    orphan_references: List[str]


def find_matching_field_names(result_fields: Iterable[Field],
                              reference_fields: Iterable[Field]) -> MatchResult:
    """Looks for matching field names in the provided results & reference field lists"""
    res_names = [f.name for f in result_fields]
    ref_names = [f.name for f in reference_fields]
    res_orphans = list(filter(lambda n: n not in ref_names, res_names))
    ref_orphans = list(filter(lambda n: n not in res_names, ref_names))
    matches = list(filter(lambda n: n not in res_orphans, res_names))
    return MatchResult(matches, res_orphans, ref_orphans)


def find_matching_file_names(results_folder: str,
                             references_folder: str) -> MatchResult:
    """Looks for matching supported files in a results & reference folder to be compared"""
    result_files = set(_find_sub_files_recursively(results_folder))
    reference_files = set(_find_sub_files_recursively(references_folder))

    matches = [filename for filename in result_files.intersection(reference_files)]
    orphan_results = [filename for filename in result_files.difference(reference_files)]
    orphan_references = [filename for filename in reference_files.difference(result_files)]
    return MatchResult(matches, orphan_results, orphan_references)


def _find_sub_files_recursively(folder) -> List[str]:
    result: list = []
    for root, _, files in walk(folder):
        result.extend(relpath(join(root, filename), folder) for filename in files)
    return result
