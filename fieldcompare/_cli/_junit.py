"""Helper function to write junit test reports"""

from typing import Optional
from xml.etree.ElementTree import Element, SubElement

from .._format import remove_color_codes
from ._test_suite import TestSuite, TestResult, TestStatus


def as_junit_xml_element(suite: TestSuite, timestamp: str) -> Element:
    xml_tree = Element("testsuite")
    xml_tree.set("name", _as_string_or("n/a", suite.name))
    xml_tree.set("tests", str(sum(1 for _ in suite)))
    xml_tree.set("disabled", "0")
    xml_tree.set("errors", str(sum(1 for t in suite if t.status == TestStatus.error)))
    xml_tree.set("failures", str(sum(1 for t in suite if t.status == TestStatus.failed)))
    xml_tree.set("skipped", str(sum(1 for t in suite if t.status == TestStatus.skipped)))
    xml_tree.set("timestamp", timestamp)
    xml_tree.set("time", _as_string_or("n/a", suite.cpu_time))

    SubElement(xml_tree, "properties")  # e.g. environment settings... currently, we have nothing
    for test in suite:
        _add_test_case(xml_tree, test, _as_string_or("n/a", suite.name))

    return xml_tree


def _as_string_or(alternative: str, input) -> str:
    if input is not None:
        return str(input)
    return alternative


def _add_test_case(test_suite: Element, test: TestResult, classname: str) -> None:
    testcase = SubElement(test_suite, "testcase")
    testcase.set("name", test.name)
    testcase.set("classname", classname)
    testcase.set("status", str(test.status).replace("TestStatus.", ""))
    testcase.set("time", _as_string_or("n/a", test.cpu_time))

    stdout = SubElement(testcase, "system-out")
    stdout.text = remove_color_codes(test.stdout)

    if test.status == TestStatus.failed:
        _set_with_message(testcase, "failure", "comparison failed", stdout.text)
    elif test.status == TestStatus.skipped:
        _set_with_message(testcase, "skipped", stdout.text)
    elif test.status == TestStatus.error:
        _set_with_message(testcase, "failure", "error upon comparison", stdout.text)
        _set_with_message(testcase, "error", "error upon comparison", stdout.text)
    elif not test:
        stderr = SubElement(testcase, "system-err")
        stderr.text = stdout.text


def _set_with_message(test_case: Element, child: str, msg: str, stdout: Optional[str] = None) -> None:
    test_case = SubElement(test_case, child)
    test_case.set("message", msg)
    if stdout is not None:
        test_case.text = stdout
