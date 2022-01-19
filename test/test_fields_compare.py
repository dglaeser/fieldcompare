"""Test the compare function for sets of fields."""

from pytest import warns
from context import fieldcompare
from fieldcompare import Field, FuzzyFieldEquality, compare_fields

def test_compare_fields_default_comparison_map():
    fields = [Field(str(i), [1, 2, 3]) for i in range(3)]
    references = [Field(str(i), [1, 2, 3]) for i in range(3)]
    passed, _ = compare_fields(fields, references)
    assert passed

def test_compare_fields_default_custom_comparison_map():
    fields = [Field(str(i), [i, i, i]) for i in range(3)]
    references = [Field(str(i), [i+1, i+1, i+1]) for i in range(3)]
    comparison_map = {"1": ["0"], "2": ["1"]}
    passed, _ = compare_fields(fields, references, field_comparisons=comparison_map)
    assert passed

def test_compare_fields_default_custom_comparison_map_missing_fields():
    fields = [Field(str(i), [i, i, i]) for i in range(3)]
    references = [Field(str(i), [i, i, i]) for i in range(3)]
    comparison_map = {"0": ["0"], "1": ["1"], "missing_field": ["missing"]}
    passed, report = compare_fields(fields, references, field_comparisons=comparison_map)
    assert not passed
    assert "missing_field" in report

def test_compare_fields_default_custom_predicate_map():
    field = [Field("field", [0.1, 0.1, 0.1])]
    reference = [Field("field", [0.1, 0.1, 0.1 + 1e-6])]
    passed, _ = compare_fields(field, reference)
    assert not passed

    def _predicate_map(f1: str, f2: str) -> FuzzyFieldEquality:
        predicate = FuzzyFieldEquality()
        predicate.set_absolute_tolerance(1e-3)
        predicate.set_relative_tolerance(1e-3)
        return predicate

    passed, _ = compare_fields(field, reference, predicate_map=_predicate_map)
    assert passed

def test_compare_fields_duplicate_fields_in_comparison_map():
    fields = [Field(str(i), [1, 2, 3]) for i in range(3)]
    references = [Field(str(i), [1, 2, 3]) for i in range(3)]
    comparison_map = {"0": ["0", "0"], "1": ["1"]}
    with warns(RuntimeWarning):
        passed, _ = compare_fields(fields, references, field_comparisons=comparison_map)
        assert passed

if __name__ == "__main__":
    test_compare_fields_default_comparison_map()
    test_compare_fields_default_custom_comparison_map()
    test_compare_fields_default_custom_comparison_map_missing_fields()
    test_compare_fields_default_custom_predicate_map()
    test_compare_fields_duplicate_fields_in_comparison_map()
