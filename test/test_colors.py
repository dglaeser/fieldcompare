"""Test text styling facilities"""

from context import fieldcompare
from fieldcompare.colors import make_colored, TextColor
from fieldcompare.colors import text_color_options
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

def test_color_context_manager():
    test_string = make_colored("hello", color=TextColor.red)
    assert "[0m" in test_string
    with text_color_options(use_colors=False, use_styles=False):
        test_string = make_colored("hello", color=TextColor.red)
        assert "[0m" not in test_string

    test_string = make_colored("hello", color=TextColor.red)
    assert "[0m" in test_string
    with text_color_options(use_colors=True, use_styles=True):
        test_string = make_colored("hello", color=TextColor.red)
        assert "[0m" in test_string

    test_string = make_colored("hello", color=TextColor.red)
    assert "[0m" in test_string

if __name__ == "__main__":
    test_deactivate_and_activate_colors()
    test_color_context_manager()
