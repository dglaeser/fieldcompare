"""Test text styling facilities"""

from context import fieldcompare
from fieldcompare.colors import make_colored, TextColor
from fieldcompare.colors import deactivate_colored_output, activate_colored_output

def test_deactivate_and_activate_colors():
    test_string = make_colored("hello", color=TextColor.red)
    assert "[0m" in test_string

    deactivate_colored_output()
    test_string = make_colored("hello", color=TextColor.red)
    assert "[0m" not in test_string

    activate_colored_output()
    test_string = make_colored("hello", color=TextColor.red)
    assert "[0m" in test_string

if __name__ == "__main__":
    test_deactivate_and_activate_colors()
