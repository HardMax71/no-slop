"""Unit tests for the flake8 plugin."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from no_slop.flake8_plugin import SlopStyleChecker

if TYPE_CHECKING:
    pass


def check_code(code: str) -> list[tuple[int, int, str, type]]:
    """Run the checker on code and return errors."""
    lines = code.splitlines()
    tree = ast.parse(code)
    checker = SlopStyleChecker(tree, lines, "test.py")
    return list(checker.run())


class TestEmojiDetection:
    """Tests for emoji detection (SLOP022)."""

    def test_emoji_in_string(self) -> None:
        code = 'x = "Hello 🎉 World"'
        errors = check_code(code)
        assert len(errors) == 1
        assert "SLOP022" in errors[0][2]
        assert "🎉" in errors[0][2]

    def test_emoji_in_comment(self) -> None:
        code = "x = 1  # 🚀 rocket ship"
        errors = check_code(code)
        assert len(errors) == 1
        assert "SLOP022" in errors[0][2]

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
        emoji_errors = [e for e in errors if "SLOP022" in e[2]]
        assert len(emoji_errors) == 0

    def test_emoji_ignored_with_noqa(self) -> None:
        code = 'x = "Hello 🎉"  # noqa: SLOP022'
        errors = check_code(code)
        assert len(errors) == 0

    def test_emoji_ignored_with_noqa_all(self) -> None:
        code = 'x = "Hello 🎉"  # noqa'
        errors = check_code(code)
        assert len(errors) == 0


class TestAsciiArtDetection:
    """Tests for ASCII art detection (SLOP021)."""

    def test_box_drawing(self) -> None:
        code = "# ╔════════════════════════╗"
        errors = check_code(code)
        assert len(errors) == 1
        assert "SLOP021" in errors[0][2]
        assert "Box-drawing" in errors[0][2]

    def test_block_characters(self) -> None:
        code = "# ████████████████████████"
        errors = check_code(code)
        assert len(errors) == 1
        assert "SLOP021" in errors[0][2]
        assert "Block-drawing" in errors[0][2]

    def test_simple_separator_allowed(self) -> None:
        code = "# ========================================="
        errors = check_code(code)
        # Simple separators should be allowed
        art_errors = [e for e in errors if "SLOP021" in e[2]]
        assert len(art_errors) == 0

    def test_section_header_allowed(self) -> None:
        code = "# === CONFIGURATION ==="
        errors = check_code(code)
        art_errors = [e for e in errors if "SLOP021" in e[2]]
        assert len(art_errors) == 0

    def test_ascii_art_ignored_with_noqa(self) -> None:
        code = "# ╔════════════════════════╗  # noqa: SLOP021"
        errors = check_code(code)
        assert len(errors) == 0


class TestExcessiveDocstring:
    """Tests for excessive docstring detection (SLOP020)."""

    def test_long_docstring_flagged(self) -> None:
        # Create a docstring that's too long relative to code
        docstring = '"""' + "\n".join(["Line " + str(i) for i in range(20)]) + '"""'
        code = f"""{docstring}

def foo() -> int:
    return 1
"""
        errors = check_code(code)
        docstring_errors = [e for e in errors if "SLOP020" in e[2]]
        assert len(docstring_errors) == 1

    def test_short_docstring_ok(self) -> None:
        code = '''"""Short module docstring."""

def foo() -> int:
    return 1
'''
        errors = check_code(code)
        docstring_errors = [e for e in errors if "SLOP020" in e[2]]
        assert len(docstring_errors) == 0


class TestLeadingComments:
    """Tests for excessive leading comment blocks (SLOP020)."""

    def test_excessive_leading_comments(self) -> None:
        comments = "\n".join([f"# Comment line {i}" for i in range(15)])
        code = f"""{comments}

def foo() -> int:
    return 1
"""
        errors = check_code(code)
        comment_errors = [e for e in errors if "SLOP020" in e[2]]
        assert len(comment_errors) == 1

    def test_short_leading_comments_ok(self) -> None:
        code = """# Author: Test
# License: MIT

def foo() -> int:
    return 1
"""
        errors = check_code(code)
        comment_errors = [e for e in errors if "SLOP020" in e[2]]
        assert len(comment_errors) == 0


class TestFileIgnores:
    """Tests for file-level ignores."""

    def test_file_ignore_all(self) -> None:
        code = """# slop: ignore-file
x = "🎉 Hello"  # Would be flagged
# ╔════════╗  # Would be flagged
"""
        errors = check_code(code)
        assert len(errors) == 0

    def test_file_ignore_specific_code(self) -> None:
        code = """# slop: ignore-file[SLOP022]
x = "🎉 Hello"  # Emoji ignored
# ╔════════╗  # ASCII art NOT ignored
"""
        errors = check_code(code)
        emoji_errors = [e for e in errors if "SLOP022" in e[2]]
        art_errors = [e for e in errors if "SLOP021" in e[2]]
        assert len(emoji_errors) == 0
        assert len(art_errors) == 1

    def test_file_ignore_multiple_codes(self) -> None:
        code = """# slop: ignore-file[SLOP021, SLOP022]
x = "🎉 Hello"  # Ignored
# ╔════════╗  # Ignored
"""
        errors = check_code(code)
        assert len(errors) == 0


class TestMultipleIgnoreCodes:
    """Tests for multiple ignore codes on one line."""

    def test_multiple_codes_in_noqa(self) -> None:
        code = 'x = "🎉"  # ╔══╗ noqa: SLOP021, SLOP022'
        errors = check_code(code)
        assert len(errors) == 0

    def test_noqa_with_other_content(self) -> None:
        # noqa can appear after other comment content
        code = 'x = "🎉"  # TODO: fix this noqa: SLOP022'
        errors = check_code(code)
        emoji_errors = [e for e in errors if "SLOP022" in e[2]]
        assert len(emoji_errors) == 0
