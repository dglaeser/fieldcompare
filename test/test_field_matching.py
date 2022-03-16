import numpy as np
from typing import List

from context import fieldcompare
from fieldcompare.field import Field
from fieldcompare.matching import MatchResult, find_matching_field_names


def empty_match_result():
    return MatchResult([], [], [])


def field(name: str):
    return Field(name, np.empty(1))


def match_result_with_no_ophans(matches: List[str]):
    return MatchResult(matches, [], [])


def test_two_empty_lists__returns_an_empty_matchresult():
    actual = find_matching_field_names([], [])

    assert actual == empty_match_result()


def test_two_lists_with_matching_fields__returns_both_fields_and_no_orphans():
    matching_name = "match"
    result_field = field(matching_name)
    reference_field = field(matching_name)

    actual = find_matching_field_names([result_field], [reference_field])

    assert actual == match_result_with_no_ophans([matching_name])


def test_non_matching_result_field__returns_no_match_and_result_orphan():
    non_matching_name = "no_match"
    result_field = field(non_matching_name)

    actual = find_matching_field_names([result_field], [])

    assert actual == MatchResult([], [non_matching_name], [])


def test_non_matching_reference_field__returns_no_match_and_reference_orphan():
    non_matching_name = "no_match"
    reference_field = field(non_matching_name)

    actual = find_matching_field_names([], [reference_field])

    assert actual == MatchResult([], [], [non_matching_name])


def test_one_matching_and_one_non_matching_result_and_reference__returns_includes_all():
    matching_name = "match"
    non_matching_result_name = "non_matching_result"
    non_matching_reference_name = "non_matching_reference"

    matching_result_field = field(matching_name)
    matching_reference_field = field(matching_name)
    non_matching_result_field = field(non_matching_result_name)
    non_matching_reference_field = field(non_matching_reference_name)

    actual = find_matching_field_names(
        [matching_result_field, non_matching_result_field],
        [matching_reference_field, non_matching_reference_field],
    )

    assert actual == MatchResult(
        [matching_name],
        [non_matching_result_name],
        [non_matching_reference_name],
    )
