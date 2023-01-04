"""In this example, we use fieldcompare to read in fields from files and compare them"""

from io import StringIO
from numpy import less, all, ndarray

from fieldcompare import FieldDataComparator, FieldComparison, DefaultFieldComparisonCallback
from fieldcompare.predicates import ExactEquality, FuzzyEquality, PredicateResult

# convenience function to read in field data from files
from fieldcompare.io import read_field_data

# Protocols you can use for type annotations
from fieldcompare import protocols


class MyPredicate:
    """Exemplary implementation for a custom predicate"""

    def __call__(self, values1: ndarray, values2: ndarray) -> PredicateResult:
        """Check if all entries of values1 are smaller than those of values2"""
        return PredicateResult(
            value=bool(all(less(values1, values2))),
            report="We could write detailed info about the predicate evaluation"
        )

    def __str__(self) -> str:
        return "My-very-own-predicate"


def _select_predicate(source_field: protocols.Field,
                      target_field: protocols.Field) -> protocols.Predicate:
    if source_field.name == "field1":
        return ExactEquality()
    return FuzzyEquality()


if __name__ == "__main__":
    # You can use the provided functions to conveniently read in fields from files
    fields: protocols.FieldData = read_field_data("example1.csv")

    # FieldData allows you to iterate over all fields and obtain their names and values
    for field in fields:
        assert field.name in ["field1", "field2"]
        print(f"Name -> values: {field.name} -> {field.values}")

    # The FieldDataComparison class provides an easy way to compare fields
    # against reference data. Here, we simply compare the fields against
    # themselves. The constructor takes the field data to be compared,
    # while the actual comparison is carried out via the call-operator.
    comparator = FieldDataComparator(source=fields, reference=fields)

    print("\nPerforming comparison...")
    result = comparator()
    print("done.")

    # The result contains a report, and it allows us to extract
    # information on all performed comparisons
    print(f"\nReport: {result.report}")

    def _print_field_comparison(field_comparison: FieldComparison) -> None:
        print(f"Field '{field_comparison.name}'")
        print(f" -- Status: {field_comparison.status}")
        print(f" -- Predicate used: {field_comparison.predicate}")
        print(f" -- Report: {field_comparison.report}")

    print("Printing reports for all comparisons:")
    for comparison in result:
        _print_field_comparison(comparison)

    # During the execution of the comparison, some information on the
    # performed comparisons was already printed to the terminal. You
    # can customize this by passing a callback function that accepts
    # a field comparison result.
    print("\nPerforming comparison without any output")
    result = comparator(fieldcomp_callback=lambda _: None)
    print("done.")

    print("\nPerforming comparison with custom output")
    result = comparator(fieldcomp_callback=lambda comp: _print_field_comparison(comp))
    print("done.")

    # You can also reuse & customize the default callback...
    print("\nPerforming comparison with modified default output (no colors)")
    result = comparator(fieldcomp_callback=DefaultFieldComparisonCallback(use_colors=False))
    print("done.")

    print("\nPerforming comparison with modified default output (increased verbosity)")
    result = comparator(fieldcomp_callback=DefaultFieldComparisonCallback(verbosity=2))
    print("done.")

    # You can also pass the output to a stream
    print("\nPerforming comparison with default output piped into a string")
    with StringIO() as stream:
        result = comparator(fieldcomp_callback=DefaultFieldComparisonCallback(stream=stream, use_colors=False))
        print("done.")
        print("Output collected as string:")
        print(stream.getvalue())

    # The comparator also allows you to select a custom predicate for
    # each pair of fields that are to be compared
    print("\nPerforming comparison with custom predicate selector and no output")
    result = comparator(
        predicate_selector=_select_predicate,
        fieldcomp_callback=lambda _: None
    )
    print("done")
    print("Printing collected results (notice the predicate choices)")
    for comparison in result:
        _print_field_comparison(comparison)

    # A predicate simply takes to arrays and returns something that fulfills the
    # `PredicateResult` protocol, i.e. something that is convertible to bool
    # and allows for gathering a report about the predicate evaluation:
    print("\nPerforming comparison with custom predicate class")
    result = comparator(
        predicate_selector=lambda _, __: MyPredicate(),
        fieldcomp_callback=DefaultFieldComparisonCallback(verbosity=2)
    )
    print("done")
    print("Our predicate evaluated to false, see the final report:")
    print(result.report)
