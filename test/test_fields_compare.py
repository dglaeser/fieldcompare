"""Test the compare function for sets of fields."""

from context import fieldcompare
from fieldcompare import Field, FuzzyEquality
from fieldcompare import (
    compare_fields_equal,
    compare_matching_fields,
    compare_matching_fields_equal
)

def test_compare_fields_default_comparison_map():
    fields = [Field(str(i), [1, 2, 3]) for i in range(3)]
    references = [Field(str(i), [1, 2, 3]) for i in range(3)]
    result, skipped = compare_matching_fields_equal(fields, references)
    assert bool(result)
    assert not skipped

def test_compare_fields_default_custom_comparison_map():
    fields = [Field(str(i), [i, i, i]) for i in range(3)]
    references = [Field(str(i), [i+1, i+1, i+1]) for i in range(3)]
    comparison_map = {"1": ["0"], "2": ["1"]}
    result = compare_fields_equal(fields, references, field_comparison_map=comparison_map)
    assert bool(result)

def test_compare_fields_default_custom_comparison_map_missing_fields():
    fields = [Field(str(i), [i, i, i]) for i in range(3)]
    references = [Field(str(i), [i, i, i]) for i in range(3)]
    comparison_map = {"0": ["0"], "1": ["1"], "missing_field": ["other_missing_field"]}
    result = compare_fields_equal(fields, references, field_comparison_map=comparison_map)
    assert any(r.result_field_name == "0" and r.reference_field_name == "0" for r in result)
    assert any(r.result_field_name == "1" and r.reference_field_name == "1" for r in result)
    assert not any(
        r.result_field_name == "missing_field" and r.reference_field_name == "other_missing_field"
        for r in result
    )

def test_compare_fields_default_custom_predicate_map():
    field = [Field("field", [0.1, 0.1, 0.1])]
    reference = [Field("field", [0.1, 0.1, 0.1 + 1e-6])]
    result, skipped = compare_matching_fields_equal(field, reference)
    assert not bool(result)
    assert not bool(skipped)

    def _predicate_map(f1: str, f2: str) -> FuzzyEquality:
        return FuzzyEquality(rel_tol=1e-3, abs_tol=1e-3)

    result, skipped = compare_matching_fields(field, reference, predicate_map=_predicate_map)
    assert bool(result)
    assert not bool(skipped)

if __name__ == "__main__":
    test_compare_fields_default_comparison_map()
    test_compare_fields_default_custom_comparison_map()
    test_compare_fields_default_custom_comparison_map_missing_fields()
    test_compare_fields_default_custom_predicate_map()
