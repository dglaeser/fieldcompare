"""Test the collection of field files to compare."""

from os import makedirs, remove, walk, rmdir
from os.path import join, exists, isdir
from typing import List

from fieldcompare._matching import find_matching_file_names, MatchResult


def _touch(file_path: str) -> None:
    with open(file_path, "w") as _:
        pass


def _create_files(folder: str, filenames: List[str]) -> None:
    for filename in filenames:
        _touch(join(folder, filename))


def _delete_files(folder: str, filenames: List[str]) -> None:
    for filename in filenames:
        remove(join(folder, filename))


def _create_folder(name: str) -> None:
    if exists(name) and isdir(name):
        _delete_folder(name)
    elif exists(name):
        _delete_files(".", [name])
    makedirs(name, exist_ok=True)


def _delete_folder(name: str) -> None:
    for root, _, files in walk(name):
        _delete_files(root, files)
    for root, folders, _ in walk(name):
        for folder in folders:
            rmdir(join(root, folder))
    rmdir(name)


def test_collect_from_same_folder():
    test_folder = "test_collector_single_folder"
    _create_folder(test_folder)
    _create_files(test_folder, ["one.csv", "two.csv"])

    result = find_matching_file_names(test_folder, test_folder)
    result.matches.sort()  # make sure the order of the matches is unique
    assert result == MatchResult(["one.csv", "two.csv"], ([], []))

    _delete_folder(test_folder)


def test_collect_missing_results():
    results_folder = "test_collector_missing_results"
    references_folder = "test_collector_missing_results_references"
    _create_folder(results_folder)
    _create_files(results_folder, ["one.csv"])
    _create_folder(references_folder)
    _create_files(references_folder, ["one.csv", "two.csv"])

    result = find_matching_file_names(results_folder, references_folder)
    assert result == MatchResult(["one.csv"], ([], ["two.csv"]))

    _delete_folder(results_folder)
    _delete_folder(references_folder)


def test_collect_missing_references():
    results_folder = "test_collector_missing_references"
    references_folder = "test_collector_missing_references_references"
    _create_folder(results_folder)
    _create_files(results_folder, ["one.csv", "two.csv"])
    _create_folder(references_folder)
    _create_files(references_folder, ["one.csv"])

    result = find_matching_file_names(results_folder, references_folder)
    assert result == MatchResult(["one.csv"], (["two.csv"], []))

    _delete_folder(results_folder)
    _delete_folder(references_folder)
