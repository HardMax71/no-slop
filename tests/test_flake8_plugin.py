from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from no_slop.flake8_plugin import SlopStyleChecker

if TYPE_CHECKING:
    pass


def check_code(code: str) -> list[tuple[int, int, str, type]]:
    lines = code.splitlines()
    tree = ast.parse(code)
    checker = SlopStyleChecker(tree, lines, "test.py")
    return list(checker.run())


class TestEmojiDetection:
    def test_emoji_in_string(self) -> None:
        code = 'x = "Hello 🎉 World"'
        errors = check_code(code)
        assert len(errors) == 1
        assert "SLP022" in errors[0][2]
        assert "🎉" in errors[0][2]

    def test_emoji_in_comment(self) -> None:
        code = "x = 1  # 🚀 rocket ship"
        errors = check_code(code)
        assert len(errors) == 1
        assert "SLP022" in errors[0][2]

    def test_multiple_emojis(self) -> None:
        code = 'msg = "🎯 ✨ 🎉"'
        errors = check_code(code)
        assert len(errors) == 1
        # All emojis should be listed
        assert "🎯" in errors[0][2]
        assert "✨" in errors[0][2]
        assert "🎉" in errors[0][2]

    def test_no_emoji_clean(self) -> None:
        code = 'x = "Hello World"'
        errors = check_code(code)
        emoji_errors = [e for e in errors if "SLP022" in e[2]]
        assert len(emoji_errors) == 0

    def test_emoji_ignored_with_noqa(self) -> None:
        code = 'x = "Hello 🎉"  # noqa: SLP022'
        errors = check_code(code)
        assert len(errors) == 0

    def test_emoji_ignored_with_noqa_all(self) -> None:
        code = 'x = "Hello 🎉"  # noqa'
        errors = check_code(code)
        assert len(errors) == 0


class TestAsciiArtDetection:
    def test_box_drawing(self) -> None:
        code = "# ╔════════════════════════╗"
        errors = check_code(code)
        assert len(errors) == 1
        assert "SLP021" in errors[0][2]
        assert "Box-drawing" in errors[0][2]

    def test_block_characters(self) -> None:
        code = "# ████████████████████████"
        errors = check_code(code)
        assert len(errors) == 1
        assert "SLP021" in errors[0][2]
        assert "Block-drawing" in errors[0][2]

    def test_simple_separator_allowed(self) -> None:
        code = "# ========================================="
        errors = check_code(code)
        # Simple separators should be allowed
        art_errors = [e for e in errors if "SLP021" in e[2]]
        assert len(art_errors) == 0

    def test_section_header_allowed(self) -> None:
        code = "# === CONFIGURATION ==="
        errors = check_code(code)
        art_errors = [e for e in errors if "SLP021" in e[2]]
        assert len(art_errors) == 0

    def test_section_header_end_allowed(self) -> None:
        code = "# IMPORTS ============"
        errors = check_code(code)
        art_errors = [e for e in errors if "SLP021" in e[2]]
        assert len(art_errors) == 0

    def test_arrow_pattern_detected(self) -> None:
        code = "# <<<<<<<<<<<<<<<<<<<<<<<<<"
        errors = check_code(code)
        assert len(errors) == 1
        assert "SLP021" in errors[0][2]
        assert "arrow" in errors[0][2].lower()

    def test_caret_arrow_pattern_detected(self) -> None:
        code = "# ^^^^^^^^^^^^^^^^^^^^^^"
        errors = check_code(code)
        assert len(errors) == 1
        assert "SLP021" in errors[0][2]

    def test_ascii_art_ignored_with_noqa(self) -> None:
        code = "# ╔════════════════════════╗  # noqa: SLP021"
        errors = check_code(code)
        assert len(errors) == 0


class TestExcessiveDocstring:
    def test_long_docstring_flagged(self) -> None:
        docstring = '"""' + "\n".join(["Line " + str(i) for i in range(20)]) + '"""'
        code = f"""{docstring}

def foo() -> int:
    return 1
"""
        errors = check_code(code)
        docstring_errors = [e for e in errors if "SLP020" in e[2]]
        assert len(docstring_errors) == 1

    def test_short_docstring_ok(self) -> None:
        code = '''"""Short module docstring."""

def foo() -> int:
    return 1
'''
        errors = check_code(code)
        docstring_errors = [e for e in errors if "SLP020" in e[2]]
        assert len(docstring_errors) == 0

    def test_expression_not_constant_ok(self) -> None:
        code = """foo()

def bar() -> int:
    return 1
"""
        errors = check_code(code)
        docstring_errors = [e for e in errors if "SLP020" in e[2]]
        assert len(docstring_errors) == 0

    def test_constant_not_string_ok(self) -> None:
        code = """42

def bar() -> int:
    return 1
"""
        errors = check_code(code)
        docstring_errors = [e for e in errors if "SLP020" in e[2]]
        assert len(docstring_errors) == 0

    def test_docstring_with_statements_only(self) -> None:
        docstring = '"""' + "\n".join(["Line " + str(i) for i in range(20)]) + '"""'
        code = f"""{docstring}

x = 1
y = 2
z = 3
"""
        errors = check_code(code)
        docstring_errors = [e for e in errors if "SLP020" in e[2]]
        assert len(docstring_errors) == 1


class TestLeadingComments:
    def test_excessive_leading_comments(self) -> None:
        comments = "\n".join([f"# Comment line {i}" for i in range(15)])
        code = f"""{comments}

def foo() -> int:
    return 1
"""
        errors = check_code(code)
        comment_errors = [e for e in errors if "SLP020" in e[2]]
        assert len(comment_errors) == 1

    def test_short_leading_comments_ok(self) -> None:
        code = """# Author: Test
# License: MIT

def foo() -> int:
    return 1
"""
        errors = check_code(code)
        comment_errors = [e for e in errors if "SLP020" in e[2]]
        assert len(comment_errors) == 0


class TestFileIgnores:
    def test_file_ignore_all(self) -> None:
        code = """# slop: ignore-file
x = "🎉 Hello"  # Would be flagged
# ╔════════╗  # Would be flagged
"""
        errors = check_code(code)
        assert len(errors) == 0

    def test_file_ignore_specific_code(self) -> None:
        code = """# slop: ignore-file[SLP022]
x = "🎉 Hello"  # Emoji ignored
# ╔════════╗  # ASCII art NOT ignored
"""
        errors = check_code(code)
        emoji_errors = [e for e in errors if "SLP022" in e[2]]
        art_errors = [e for e in errors if "SLP021" in e[2]]
        assert len(emoji_errors) == 0
        assert len(art_errors) == 1

    def test_file_ignore_multiple_codes(self) -> None:
        code = """# slop: ignore-file[SLP021, SLP022]
x = "🎉 Hello"  # Ignored
# ╔════════╗  # Ignored
"""
        errors = check_code(code)
        assert len(errors) == 0


class TestMultipleIgnoreCodes:
    def test_multiple_codes_in_noqa(self) -> None:
        code = 'x = "🎉"  # ╔══╗ noqa: SLP021, SLP022'
        errors = check_code(code)
        assert len(errors) == 0

    def test_noqa_with_other_content(self) -> None:
        code = 'x = "🎉"  # TODO: fix this noqa: SLP022'
        errors = check_code(code)
        emoji_errors = [e for e in errors if "SLP022" in e[2]]
        assert len(emoji_errors) == 0


class TestLocalImports:
    def test_local_import_detected(self) -> None:
        code = """
def foo():
    import os
    return os.getcwd()
"""
        errors = check_code(code)
        local_errors = [e for e in errors if "SLP023" in e[2]]
        assert len(local_errors) == 1
        assert "Local import" in local_errors[0][2]

    def test_local_from_import_detected(self) -> None:
        code = """
def foo():
    from os import path
    return path.exists(".")
"""
        errors = check_code(code)
        local_errors = [e for e in errors if "SLP023" in e[2]]
        assert len(local_errors) == 1
        assert "from os import path" in local_errors[0][2]

    def test_module_level_import_ok(self) -> None:
        code = """
import os

def foo():
    return os.getcwd()
"""
        errors = check_code(code)
        local_errors = [e for e in errors if "SLP023" in e[2]]
        assert len(local_errors) == 0

    def test_type_checking_import_ok(self) -> None:
        code = """
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

def foo(x: "Sequence[int]") -> int:
    return x[0]
"""
        errors = check_code(code)
        local_errors = [e for e in errors if "SLP023" in e[2]]
        assert len(local_errors) == 0

    def test_type_checking_attribute_import_ok(self) -> None:
        code = """
import typing

if typing.TYPE_CHECKING:
    from collections.abc import Sequence

def foo(x: "Sequence[int]") -> int:
    return x[0]
"""
        errors = check_code(code)
        local_errors = [e for e in errors if "SLP023" in e[2]]
        assert len(local_errors) == 0

    def test_local_import_ignored_with_noqa(self) -> None:
        code = """
def foo():
    import os  # noqa: SLP023
    return os.getcwd()
"""
        errors = check_code(code)
        local_errors = [e for e in errors if "SLP023" in e[2]]
        assert len(local_errors) == 0

    def test_nested_function_local_import(self) -> None:
        code = """
def outer():
    def inner():
        import json
        return json.dumps({})
    return inner()
"""
        errors = check_code(code)
        local_errors = [e for e in errors if "SLP023" in e[2]]
        assert len(local_errors) == 1

    def test_async_function_local_import(self) -> None:
        code = """
async def fetch():
    import aiohttp
    return aiohttp
"""
        errors = check_code(code)
        local_errors = [e for e in errors if "SLP023" in e[2]]
        assert len(local_errors) == 1

    def test_class_method_local_import(self) -> None:
        code = """
class Foo:
    def bar(self):
        import sys
        return sys.version
"""
        errors = check_code(code)
        local_errors = [e for e in errors if "SLP023" in e[2]]
        assert len(local_errors) == 1

    def test_regular_if_block_visited(self) -> None:
        code = """
if True:
    x = 1

def foo():
    import os
    return os.getcwd()
"""
        errors = check_code(code)
        local_errors = [e for e in errors if "SLP023" in e[2]]
        assert len(local_errors) == 1

    def test_if_with_other_condition_not_type_checking(self) -> None:
        code = """
DEBUG = True
if DEBUG:
    from collections.abc import Sequence

def foo():
    import os
    return os.getcwd()
"""
        errors = check_code(code)
        local_errors = [e for e in errors if "SLP023" in e[2]]
        assert len(local_errors) == 1
