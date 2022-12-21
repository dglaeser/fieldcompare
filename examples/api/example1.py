"""In this example, we use fieldcompare to read in fields from files and compare them"""

from os import remove
from numpy import less, all, ndarray

from fieldcompare import FieldDataComparator
from fieldcompare.predicates import ExactEquality, FuzzyEquality, PredicateResult

# convenience function to read in field data from files
from fieldcompare.io import read_field_data

# Protocols you can use for type annotations
from fieldcompare import protocols


class MyPredicate:
    def __call__(self, values1: ndarray, values2: ndarray) -> PredicateResult:
        """Check if all entries of values1 are smaller than those of values2"""
        return PredicateResult(
            value=bool(all(less(values1, values2))),
            report="We could write detailed info about the predicate evaluation"
        )

    def __str__(self) -> str:
        return "My-very-own-predicate"


def _write_example_csv_file() -> None:
    with open("example2.csv", "w") as csv_file:
        csv_file.write("field1,field2\n")
        csv_file.write("1.0,2.0\n")
        csv_file.write("2.0,3.0\n")


def _remove_example_csv_file() -> None:
    remove("example2.csv")


def _select_predicate(source_field: protocols.Field,
                      target_field: protocols.Field) -> protocols.Predicate:
    if source_field.name == "field1":
        return ExactEquality()
    return FuzzyEquality()


if __name__ == "__main__":
    _write_example_csv_file()

    # you may also use the provided functions for reading in fields from files
    fields: protocols.FieldData = read_field_data("example2.csv")

    # the result allows you to iterate over all fields
    # obtain their names and field values
    for field in fields:
        assert field.name in ["field1", "field2"]
        print(f"Name -> values: {field.name} -> {field.values}")

    # The FieldDataComparison class provides an easy way to compare fields
    # against reference data. Here, we simply compare the fields against
    # themselves. The constructor takes the field data to be compared,
    # while the actual comparison is carried out via the call-operator.
    comparator = FieldDataComparator(source=fields, reference=fields)
    comparisons = comparator()

    def _print_field_comp_result(field_comparison) -> None:
        print(f"\nResults for field '{field_comparison.name}'")
        print(f" -- Status: {field_comparison.status}")
        print(f" -- Predicate used: {field_comparison.predicate}")
        print(f" -- Report: {field_comparison.report}")

    # The result contains the results of the comparisons of all fields
    # contained in the source and reference data
    for field_comparison in comparisons:
        _print_field_comp_result(field_comparison)

    # As can be seen from the above, for each comparison one can get
    # information on the predicate that was used for the comparison.
    # You can also specify which predicate to use:
    comparisons = comparator(predicate_selector=_select_predicate)
    for field_comparison in comparisons:
        _print_field_comp_result(field_comparison)

    # For very large fields, the individual comparisons may take some
    # time. In case you want to generate output during the comparisons,
    # you can pass a callback function that is invoked with each result
    # once it is finished. To achieve the same output as before, we can write:
    comparisons = comparator(
        predicate_selector=_select_predicate,
        fieldcomp_callback=lambda field_comp: _print_field_comp_result(field_comp)
    )

    # A predicate simply takes to arrays and returns something that fulfills the
    # `PredicateResult` protocol, i.e. something that is convertible to bool
    # and allows for gathering a report about the predicate evaluation:
    copmarisons = comparator(
        predicate_selector=lambda _, __: MyPredicate(),
        fieldcomp_callback=lambda field_comp: _print_field_comp_result(field_comp)
    )

    _remove_example_csv_file()
