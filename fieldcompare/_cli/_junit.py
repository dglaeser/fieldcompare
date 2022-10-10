"""Helper class to write junit test reports"""

from typing import Optional
from xml.etree.ElementTree import Element, SubElement

from .._colors import remove_color_codes
from .._comparison import ComparisonSuite, Comparison, Status


class TestSuite:
    def __init__(self,
                 name: str,
                 comps: ComparisonSuite,
                 timestamp: str,
                 cpu_time: float) -> None:
        self._name = name
        self._comparisons = comps
        self._cpu_time = cpu_time
        self._time_stamp = timestamp

    def as_xml(self) -> Element:
        test_suite = Element("testsuite")
        test_suite.set("name", self._name)
        test_suite.set("tests", str(self._comparisons.size))
        test_suite.set("disabled", "0")
        test_suite.set("errors", str(sum(1 for c in self._comparisons if c.status == Status.error)))
        test_suite.set("failures", str(sum(1 for c in self._comparisons if c.status == Status.failed)))
        test_suite.set("skipped", str(sum(1 for c in self._comparisons if c.status == Status.skipped)))
        test_suite.set("timestamp", self._time_stamp)
        test_suite.set("time", str(self._cpu_time))

        self._add_properties(test_suite)
        for comp in self._comparisons:
            self._add_test_case(test_suite, comp)

        return test_suite

    def _add_properties(self, test_suite: Element) -> None:
        SubElement(test_suite, "properties")

    def _add_test_case(self, test_suite: Element, comparison: Comparison) -> None:
        testcase = SubElement(test_suite, "testcase")
        testcase.set("name", comparison.name)
        testcase.set("classname", self._name)
        testcase.set("status", str(comparison.status).replace("Status.", ""))
        testcase.set("time", str(comparison.cpu_time))

        stdout = SubElement(testcase, "system-out")
        stdout.text = remove_color_codes(comparison.stdout)

        if comparison.status == Status.failed:
            self._set_with_message(testcase, "failure", "comparison failed", stdout.text)
        elif comparison.status == Status.skipped:
            self._set_with_message(testcase, "skipped", stdout.text)
        elif comparison.status == Status.error:
            self._set_with_message(testcase, "failure", "error upon comparison", stdout.text)
            self._set_with_message(testcase, "error", "error upon comparison", stdout.text)
        elif not comparison:
            stderr = SubElement(testcase, "system-err")
            stderr.text = stdout.text

    def _set_with_message(self, test_case: Element, child: str, msg: str, stdout: Optional[str] = None) -> None:
        test_case = SubElement(test_case, child)
        test_case.set("message", msg)
        if stdout is not None:
            test_case.text = stdout
