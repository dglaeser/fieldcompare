# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import List

from fieldcompare._numpy_utils import make_array
from fieldcompare._field import Field
from fieldcompare._matching import find_matches_by_name


def make_field(name: str):
    return Field(name, make_array([]))


def test_match_result_with_reference_orphan():
    matching_name = "match"
    non_matching_name = "no_match"
    result_field = [make_field(matching_name)]
    reference_fields = [make_field(matching_name), make_field(non_matching_name)]

    query = find_matches_by_name(result_field, reference_fields)
    assert list(f.name for f, _ in query.matches) == ["match"]
    assert list(f.name for _, f in query.matches) == ["match"]
    assert list(f.name for f in query.orphans_in_reference) == ["no_match"]
    assert list(query.orphans_in_source) == []


def test_match_result_with_source_orphan():
    matching_name = "match"
    non_matching_name = "no_match"
    result_field = [make_field(matching_name), make_field(non_matching_name)]
    reference_fields = [make_field(matching_name)]

    query = find_matches_by_name(result_field, reference_fields)
    assert list(f.name for f, _ in query.matches) == ["match"]
    assert list(f.name for _, f in query.matches) == ["match"]
    assert list(f.name for f in query.orphans_in_source) == ["no_match"]
    assert list(query.orphans_in_reference) == []


def test_two_empty_lists__returns_an_empty_matchresult():
    query = find_matches_by_name([], [])
    assert query.matches == []
    assert query.orphans_in_source == []
    assert query.orphans_in_reference == []


def test_two_lists_with_matching_fields__returns_both_fields_and_no_orphans():
    matching_name = "match"
    result_field = make_field(matching_name)
    reference_field = make_field(matching_name)
    query = find_matches_by_name([result_field], [reference_field])
    assert list(f.name for f, _ in query.matches) == ["match"]
    assert query.orphans_in_source == []
    assert query.orphans_in_reference == []


def test_non_matching_result_field__returns_no_match_and_result_orphan():
    non_matching_name = "no_match"
    result_field = make_field(non_matching_name)
    query = find_matches_by_name([result_field], [])
    assert query.matches == []
    assert list(f.name for f in query.orphans_in_source) == ["no_match"]
    assert query.orphans_in_reference == []


def test_non_matching_reference_field__returns_no_match_and_reference_orphan():
    non_matching_name = "no_match"
    reference_field = make_field(non_matching_name)
    query = find_matches_by_name([], [reference_field])
    assert query.matches == []
    assert list(f.name for f in query.orphans_in_reference) == ["no_match"]
    assert query.orphans_in_source == []


def test_one_matching_and_one_non_matching_result_and_reference__returns_includes_all():
    matching_name = "match"
    non_matching_result_name = "non_matching_result"
    non_matching_reference_name = "non_matching_reference"

    matching_result_field = make_field(matching_name)
    matching_reference_field = make_field(matching_name)
    non_matching_result_field = make_field(non_matching_result_name)
    non_matching_reference_field = make_field(non_matching_reference_name)

    query = find_matches_by_name(
        [matching_result_field, non_matching_result_field],
        [matching_reference_field, non_matching_reference_field],
    )

    assert list(f.name for f, _ in query.matches) == ["match"]
    assert list(f.name for f in query.orphans_in_source) == ["non_matching_result"]
    assert list(f.name for f in query.orphans_in_reference) == ["non_matching_reference"]
