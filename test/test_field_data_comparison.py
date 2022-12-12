from __future__ import annotations
from typing import Iterator
from random import Random
from io import StringIO

from fieldcompare import Field, FieldDataComparison
from fieldcompare import protocols
from fieldcompare.predicates import DefaultEquality
from fieldcompare._array import Array, make_array


class MockDomain:
    def equals(self, other: MockDomain):
        return True


class MockFieldData(protocols.FieldData):
    def __init__(self,
                 num_fields: int = 1,
                 perturbation: float = 0.0) -> None:
        self._random_instance = Random(1234)
        self._perturbation = perturbation
        self._fields = list(
            Field(f"f_{i}", self._test_array())
            for i in range(num_fields)
        )

    @property
    def domain(self) -> MockDomain:
        return MockDomain()

    def __iter__(self) -> Iterator[Field]:
        return iter(self._fields)

    def permuted(self, permutation) -> MockDomain:
        raise NotImplementedError("Permutation of mock field data")

    def _test_array(self) -> Array:
        return make_array([
            42.0 + self._random_instance.uniform(0.0, self._perturbation),
            43.0,
            44.0
        ])


def get_number_of_lines(msg: str) -> int:
    return len(list(msg.strip("\n").split("\n")))


def compare_and_stream_output(source, reference):
    out_stream = StringIO()
    comparison = FieldDataComparison(source, reference)
    suite = comparison(
        predicate_selector=lambda _, __: DefaultEquality(),
        fieldcomp_callback=lambda p: out_stream.write("--\n")
    )
    return suite, out_stream.getvalue()


def test_field_data_comparison():
    source = MockFieldData()
    reference = MockFieldData()
    suite, stdout = compare_and_stream_output(source, reference)

    assert suite
    assert len(list(suite)) == 1
    assert len(list(suite.passed)) == 1
    assert len(list(suite.failed)) == 0
    assert len(list(suite.skipped)) == 0
    assert get_number_of_lines(stdout) == 1


def test_field_data_comparison_missing_source():
    source = MockFieldData()
    reference = MockFieldData(num_fields=2)
    suite, stdout = compare_and_stream_output(source, reference)

    assert suite
    assert len(list(suite)) == 2
    assert len(list(suite.passed)) == 1
    assert len(list(suite.failed)) == 0
    assert len(list(suite.skipped)) == 1
    assert get_number_of_lines(stdout) == 1


def test_field_data_comparison_missing_reference():
    source = MockFieldData(num_fields=2)
    reference = MockFieldData(num_fields=1)
    suite, stdout = compare_and_stream_output(source, reference)

    assert suite
    assert len(list(suite)) == 2
    assert len(list(suite.passed)) == 1
    assert len(list(suite.failed)) == 0
    assert len(list(suite.skipped)) == 1
    assert get_number_of_lines(stdout) == 1


def test_failing_field_data_comparison():
    source = MockFieldData(num_fields=1)
    reference = MockFieldData(num_fields=1, perturbation=0.01)
    suite, stdout = compare_and_stream_output(source, reference)

    assert not suite
    assert len(list(suite)) == 1
    assert len(list(suite.passed)) == 0
    assert len(list(suite.failed)) == 1
    assert len(list(suite.skipped)) == 0
    assert get_number_of_lines(stdout) == 1
