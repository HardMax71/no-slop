
import ast

from no_slop.rules.flake8.ai_artifacts import (
    check_conversational_residue,
    check_generic_names,
    check_obvious_comments,
)
from no_slop.rules.flake8.base import IgnoreHandler


class MockChecker:
    name = "no-slop"

class TestConversationalResidue:
    def test_conversational_patterns_detected(self):
        lines = [
            "# Here is the updated code",
            "def foo():",
            "    # As an AI, I suggest this",
            "    pass",
            "# Hope this helps",
            "# I have implemented the function",
        ]
        ignores = IgnoreHandler(lines)
        errors = list(check_conversational_residue(lines, ignores, MockChecker))

        assert len(errors) == 4
        assert "SLP030" in errors[0][2]  # Here is the updated code
        assert "SLP030" in errors[1][2]  # As an AI
        assert "SLP030" in errors[2][2]  # Hope this helps
        assert "SLP030" in errors[3][2]  # I have implemented

        assert errors[0][0] == 1  # Line numbers
        assert errors[1][0] == 3
        assert errors[2][0] == 5
        assert errors[3][0] == 6

    def test_language_hints_detected(self):
        lines = [
            "# Python",
            "print('hello')",
            "  # python  ",
            "x = 1",
            "# c++",
        ]
        ignores = IgnoreHandler(lines)
        errors = list(check_conversational_residue(lines, ignores, MockChecker))
        assert len(errors) == 2  # # Python and # python
        # # c++ is not in the default regex list in ai_artifacts.py (only vbnet, javascript, python, cpp, csharp, java)
        # Wait, cpp IS in the list. Let's check regex: re.compile(r"^\s*#\s*(vbnet|javascript|python|cpp|csharp|java)\s*$", re.IGNORECASE)
        # "# c++" does not match "cpp".

    def test_clean_comments_ok(self):
        lines = [
            "# This is a normal comment",
            "# TODO: fix this",
            "x = 1  # End of line comment",
        ]
        ignores = IgnoreHandler(lines)
        errors = list(check_conversational_residue(lines, ignores, MockChecker))
        assert len(errors) == 0

    def test_ignored_with_noqa(self):
        lines = [
            "# Here is the code  # noqa: SLP030",
            "# As an AI  # noqa",
        ]
        ignores = IgnoreHandler(lines)
        errors = list(check_conversational_residue(lines, ignores, MockChecker))
        assert len(errors) == 0


class TestObviousComments:
    def test_obvious_comments_detected(self):
        lines = [
            "# Import modules",
            "import os",
            "# Define function",
            "def my_func():",
            "    # Return value",
            "    return 1",
            "    # Increment i",
            "    i += 1",
        ]
        ignores = IgnoreHandler(lines)
        errors = list(check_obvious_comments(lines, ignores, MockChecker))

        assert len(errors) == 4
        assert "SLP031" in errors[0][2]
        assert "SLP031" in errors[1][2]
        assert "SLP031" in errors[2][2]
        assert "SLP031" in errors[3][2]

    def test_useful_comments_ok(self):
        lines = [
            "# Import os for file handling",
            "import os",
            "# Calculate the total",
            "def calc():",
            "    pass",
        ]
        ignores = IgnoreHandler(lines)
        errors = list(check_obvious_comments(lines, ignores, MockChecker))
        assert len(errors) == 0

    def test_ignored_with_noqa(self):
        lines = [
            "# Import modules",
            "import os  # noqa: SLP031",
        ]
        ignores = IgnoreHandler(lines)
        errors = list(check_obvious_comments(lines, ignores, MockChecker))
        assert len(errors) == 0


class TestGenericNames:
    def test_generic_args_detected(self):
        code = """
def process(data, res):
    pass

async def fetch(url, val):
    pass
        """
        tree = ast.parse(code)
        ignores = IgnoreHandler(code.splitlines())
        errors = list(check_generic_names(tree, ignores, MockChecker))

        assert len(errors) == 3
        assert "SLP032" in errors[0][2] # data
        assert "SLP032" in errors[1][2] # res
        assert "SLP032" in errors[2][2] # val

    def test_specific_names_ok(self):
        code = """
def process(user_data, result_list):
    pass
        """
        tree = ast.parse(code)
        ignores = IgnoreHandler(code.splitlines())
        errors = list(check_generic_names(tree, ignores, MockChecker))
        assert len(errors) == 0

    def test_ignored_with_noqa(self):
        code = """
def process(data):  # noqa: SLP032
    pass
        """
        tree = ast.parse(code)
        ignores = IgnoreHandler(code.splitlines())
        errors = list(check_generic_names(tree, ignores, MockChecker))
        assert len(errors) == 0
