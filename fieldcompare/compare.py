"""Functions for comparing fields."""

from warnings import warn
from typing import Callable, Iterable, Tuple, List, Dict

from .field import Field
from .predicates import DefaultFieldEquality, PredicateResult
from ._common import _style_text, TextColor, TextStyle


FieldPredicate = Callable[[Field, Field], PredicateResult]
PredicateMap = Callable[[str, str], FieldPredicate]
FieldComparisonMap = Dict[str, List[str]]


def matching_names_map(first: Iterable[Field],
                       second: Iterable[Field]) -> dict:
    names1 = [f.name for f in first]
    names2 = [f.name for f in second]
    ignoreds = list(filter(lambda n: n not in names2, names1))
    if ignoreds:
        warn(RuntimeWarning(
            f"Some fields are not present in the second list and will be ignored: {ignoreds}",
        ))
    considered = list(filter(lambda n: n not in ignoreds, names1))
    return {name: [name] for name in considered}


def compare_fields(first: Iterable[Field],
                   second: Iterable[Field],
                   field_comparisons: FieldComparisonMap = None,
                   predicate_map: PredicateMap = None,
                   report_verbosity_level: int = 1) -> Tuple[bool, str]:
    if field_comparisons is None:
        field_comparisons = matching_names_map(first, second)
    if predicate_map is None:
        predicate_map = _default_predicate_map

    todo_comparisons = _remove_duplicates({
        name: field_comparisons[name] for name in field_comparisons
    })

    report = ""
    fail_count = 0
    for field1 in first:
        if field1.name not in field_comparisons:
            continue
        for field2 in second:
            if field2.name in field_comparisons[field1.name]:
                passed, sub_report = _compare_field(
                    field1,
                    field2,
                    predicate_map(field1.name, field2.name),
                    report_verbosity_level
                )
                todo_comparisons[field1.name].remove(field2.name)
                if report_verbosity_level > 0:
                    report += sub_report + "\n"
                if not passed:
                    fail_count += 1

    passed = True
    if any(refs for refs in todo_comparisons.values()):
        passed = False
        report += "The following field pairs have not been found:\n"
        report += "\n".join([
            str((name, ref)) for name in todo_comparisons for ref in todo_comparisons[name]
        ])
        report += "\n"

    if fail_count > 0:
        passed = False
        report += f"{fail_count} out of {len(field_comparisons)} comparisons failed\n"
    report += "Overall status: {}".format(_get_comparison_result_status_message(passed))
    return passed, report


def _default_predicate_map(field1_name: str, field2_name: str) -> FieldPredicate:
    return DefaultFieldEquality(require_equal_names=False)


def _remove_duplicates(field_comparisons: dict) -> dict:
    duplicates: dict = {}
    for field_name in field_comparisons:
        references = field_comparisons[field_name]
        unique_references = list(set(field_comparisons[field_name]))
        if len(unique_references) != len(references):
            duplicates[field_name] = [
                ref for ref in unique_references if references.count(ref) > 1
            ]
            field_comparisons[field_name] = unique_references
    if duplicates:
        warn(RuntimeWarning(
            "Found and removed duplicates in the given field comparison map: {}"
            .format([(n, ref) for n in duplicates for ref in duplicates[n]])
        ), stacklevel=1)
    return field_comparisons


def _compare_field(first: Field,
                   second: Field,
                   predicate: FieldPredicate,
                   report_verbosity_level: int) -> Tuple[bool, str]:
    def _make_bright(text: str) -> str:
        return _style_text(text, style=TextStyle.bright)

    result = predicate(first, second)
    report = "Comparison of fields '{}' and '{}' ... {}".format(
        _make_bright(first.name),
        _make_bright(second.name),
        _get_comparison_result_status_message(bool(result))
    )

    def _indent_after_first_line(text: str, ind_level: int) -> str:
        lines = text.split("\n")
        lines[1:] = [" "*ind_level + _line for _line in lines[1:]]
        return "\n".join(lines)

    def _get_report_info_string(attribute: str, message: str) -> str:
        attr_length = len(attribute)
        return " -- {}: {}".format(
            _make_bright(attribute),
            _indent_after_first_line(message, 6 + attr_length)
        )

    if not result or report_verbosity_level > 1:
        if result.predicate_info:
            report += "\n" + _get_report_info_string("Predicate", result.predicate_info)
        if result.report:
            report += "\n" + _get_report_info_string("Report", result.report)

    return bool(result), report


def _get_comparison_result_status_message(result: bool) -> str:
    if result:
        return _style_text("PASSED", color=TextColor.green, style=TextStyle.bright)
    return _style_text("FAILED", color=TextColor.red, style=TextStyle.bright)
