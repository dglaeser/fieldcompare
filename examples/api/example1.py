"""In this example, we use fieldcompare to check fields for equality"""

from fieldcompare import make_array
from fieldcompare import DefaultEquality, FuzzyEquality

# fieldcompare uses predicate classes to compare two data arrays,
# which can be used programmatically. Here, we use the default
# equality predicate, which checks for fuzzy equality for floating
# point types and exact equality for e.g. integers
equal = DefaultEquality()

# we can now check scalar values for (fuzzy) equality
assert equal(1.0, 1.0)
assert equal(1, 1)

# but more importantly, we can compare lists of values
assert equal([0, 1], [0, 1])
assert not equal([0, 1], [0, 1.2])
assert equal(["field_compare"], ["field_compare"])
assert not equal(["field_compare"], ["field_compare_2"])

# the most efficient way to compare large lists is by
# passing in "arrays" (or ndarrays from numpy). You can
# construct arrays from lists using the make_array function.
assert equal(make_array([0, 1]), make_array([0, 1]))

# Let's now test two data arrays, where one is slightly perturbed
perturbation = 1e-12
data_array_1 = make_array([0.0, 1.0, 2.0])
data_array_2 = make_array([0.0, 1.0, 2.0 + perturbation])

# the perturbation is small enough to yield equality with the default tolerance
assert equal(data_array_1, data_array_2)

# But we can define lower tolerances to be used by the predicate
low_tolerance_equal = DefaultEquality(rel_tol=1e-14, abs_tol=1e-14)
assert not low_tolerance_equal(data_array_1, data_array_2)

# You can also enforce usage of the fuzzy equality predicate, independent of the data type
fuzzy_equal = FuzzyEquality()
low_tolerance_fuzzy_equal = FuzzyEquality(rel_tol=1e-14, abs_tol=1e-14)
assert fuzzy_equal(data_array_1, data_array_2)
assert not low_tolerance_fuzzy_equal(data_array_1, data_array_2)

# Both the fuzzy and default equality predicates allow modification of the tolerances
low_tolerance_equal.absolute_tolerance = 1e-3
low_tolerance_equal.relative_tolerance = 1e-3
low_tolerance_fuzzy_equal.absolute_tolerance = 1e-3
low_tolerance_fuzzy_equal.relative_tolerance = 1e-3
assert low_tolerance_equal(data_array_1, data_array_2)
assert low_tolerance_fuzzy_equal(data_array_1, data_array_2)

# The result of a call to a predicate yields a boolean-testable type, which is the
# way we have used it so far. But, that type contains information on the used predicate,
# the result of the check and a report with additional info on what occurred during the check.
low_tolerance_fuzzy_equal.absolute_tolerance = 1e-14
low_tolerance_fuzzy_equal.relative_tolerance = 1e-14
check = low_tolerance_fuzzy_equal(data_array_1, data_array_2)
print(f"Boolean result of the check:\n{check.value}")
print(f"Information on the predicate used:\n{check.predicate_info}")
print(f"Report on the check itself:\n{check.report}")
