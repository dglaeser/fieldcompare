"""Test equality of fields read from vtk files"""

from context import fieldcompare
from fieldcompare._common import deactivate_colored_output, _style_text, TextColor

def test_deactivate_colors():
    test_string = _style_text("hello", color=TextColor.red)
    assert "[0m" in test_string

    deactivate_colored_output()
    test_string = _style_text("hello", color=TextColor.red)
    assert "[0m" not in test_string

if __name__ == "__main__":
    test_deactivate_colors()
