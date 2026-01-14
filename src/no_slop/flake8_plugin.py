from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator

__all__ = ["SlopStyleChecker"]

EMOJI_PATTERN = re.compile(
    "["
    "\U0001f600-\U0001f64f"
    "\U0001f300-\U0001f5ff"
    "\U0001f680-\U0001f6ff"
    "\U0001f1e0-\U0001f1ff"
    "\U00002702-\U000027b0"
    "\U0001f900-\U0001f9ff"
    "\U0001fa00-\U0001fa6f"
    "\U0001fa70-\U0001faff"
    "\U00002600-\U000026ff"
    "\U0001f700-\U0001f77f"
    "]+",
    flags=re.UNICODE,
)

ASCII_ART_PATTERNS = [
    re.compile(r"[│┃┆┇┊┋|]{3,}"),
    re.compile(r"[─━┄┅┈┉]{5,}"),
    re.compile(r"[╔╗╚╝╠╣╦╩╬═║]+"),
    re.compile(r"[┌┐└┘├┤┬┴┼─│]+"),
    re.compile(r"[▀▁▂▃▄▅▆▇█▉▊▋▌▍▎▏]+"),
    re.compile(r"[░▒▓]+"),
    re.compile(r"[★☆✦✧◆◇○●]+"),
    re.compile(r"(<{5,}|>{5,})"),
    re.compile(r"(\^{5,}|v{5,})"),
]

NOQA_PATTERN = re.compile(r"#.*\bnoqa\b(?::\s*([A-Z0-9,\s]+))?", re.IGNORECASE)
FILE_IGNORE_PATTERN = re.compile(
    r"#\s*slop:\s*ignore-file(?:\[([A-Z0-9,\s]+)\])?", re.IGNORECASE
)

MAX_MODULE_DOCSTRING_LINES = 5
MAX_DOCSTRING_CODE_RATIO = 0.3


class SlopStyleChecker:
    """Flake8 checker for stylistic AI-slop patterns."""

    name = "no-slop"
    version = "0.1.0"

    def __init__(self, tree: ast.Module, lines: list[str], filename: str = "stdin"):
        self.tree = tree
        self.lines = lines
        self.filename = filename
        self._file_ignores: set[str] = set()
        self._line_ignores: dict[int, set[str]] = {}
        self._parse_ignores()

    def _parse_ignores(self) -> None:
        """Parse noqa comments and file-level ignores."""
        for i, line in enumerate(self.lines, 1):
            if i <= 10:
                file_match = FILE_IGNORE_PATTERN.search(line)
                if file_match:
                    codes = file_match.group(1)
                    if codes:
                        self._file_ignores.update(
                            c.strip().upper() for c in codes.split(",")
                        )
                    else:
                        self._file_ignores.add("*")

            noqa_match = NOQA_PATTERN.search(line)
            if noqa_match:
                codes = noqa_match.group(1)
                if codes:
                    self._line_ignores[i] = {
                        c.strip().upper() for c in codes.split(",")
                    }
                else:
                    self._line_ignores[i] = {"*"}

    def _should_ignore(self, line: int, code: str) -> bool:
        """Check if an error should be ignored."""
        code = code.upper()
        if "*" in self._file_ignores or code in self._file_ignores:
            return True
        if line in self._line_ignores:
            ignores = self._line_ignores[line]
            if "*" in ignores or code in ignores:
                return True
        return False

    def run(self) -> Generator[tuple[int, int, str, type], None, None]:
        """Run all style checks and yield errors."""
        yield from self._check_module_docstring()
        yield from self._check_leading_comments()
        yield from self._check_ascii_art()
        yield from self._check_emojis()

    def _check_module_docstring(
        self,
    ) -> Iterator[tuple[int, int, str, type]]:
        """Check for excessive module docstrings."""
        if not self.tree.body:
            return

        first_node = self.tree.body[0]
        if not isinstance(first_node, ast.Expr):
            return
        if not isinstance(first_node.value, ast.Constant):
            return
        if not isinstance(first_node.value.value, str):
            return

        docstring = first_node.value.value
        doc_lines = docstring.strip().splitlines()
        doc_line_count = len(doc_lines)

        if doc_line_count <= MAX_MODULE_DOCSTRING_LINES:
            return

        code_lines = 0
        for node in self.tree.body[1:]:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                code_lines += (node.end_lineno or node.lineno) - node.lineno + 1
            elif not isinstance(node, ast.Expr):
                code_lines += 1

        if code_lines > 0:
            ratio = doc_line_count / max(code_lines, 1)
            if ratio > MAX_DOCSTRING_CODE_RATIO or doc_line_count > 15:
                if not self._should_ignore(first_node.lineno, "SLOP020"):
                    yield (
                        first_node.lineno,
                        0,
                        f"SLOP020 Excessive module docstring ({doc_line_count} lines). "
                        "Keep docs near the code they document.",
                        type(self),
                    )

    def _check_leading_comments(
        self,
    ) -> Iterator[tuple[int, int, str, type]]:
        """Check for excessive leading comment blocks."""
        comment_lines = 0
        first_comment_line = None

        for i, line in enumerate(self.lines):
            stripped = line.strip()
            if stripped.startswith("#"):
                if first_comment_line is None:
                    first_comment_line = i + 1
                comment_lines += 1
            elif stripped == "":
                continue
            else:
                break

        if comment_lines > 10 and first_comment_line is not None:
            if not self._should_ignore(first_comment_line, "SLOP020"):
                yield (
                    first_comment_line,
                    0,
                    f"SLOP020 Excessive leading comment block ({comment_lines} lines). "
                    "Keep docs near the code they document.",
                    type(self),
                )

    def _check_ascii_art(self) -> Iterator[tuple[int, int, str, type]]:
        """Check for ASCII art patterns."""
        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()

            if stripped.startswith("#"):
                after_hash = stripped[1:].strip()
                if re.match(r"^[-=*~#]{3,}$", after_hash):
                    continue
                if re.match(r"^[A-Z][A-Z0-9 _:]+[-=*~#]{3,}$", after_hash):
                    continue
                if re.match(
                    r"^[-=*~#]{3,}\s+[A-Z][A-Za-z0-9 _:]+\s*[-=*~#]*$", after_hash
                ):
                    continue

            for pattern in ASCII_ART_PATTERNS:
                if pattern.search(line):
                    if self._should_ignore(i, "SLOP021"):
                        break

                    if re.search(r"[╔╗╚╝╠╣╦╩╬║│┃┌┐└┘├┤┬┴┼]", line):
                        yield (
                            i,
                            0,
                            "SLOP021 Box-drawing ASCII art detected. Keep code clean.",
                            type(self),
                        )
                        break

                    if re.search(r"[▀▁▂▃▄▅▆▇█▉▊▋▌▍▎▏░▒▓]{3,}", line):
                        yield (
                            i,
                            0,
                            "SLOP021 Block-drawing ASCII art detected. Keep code clean.",
                            type(self),
                        )
                        break

                    if re.search(r"[<>]{10,}|[\^v]{10,}", line):
                        yield (
                            i,
                            0,
                            "SLOP021 Decorative arrow pattern detected. Keep code clean.",
                            type(self),
                        )
                        break

    def _check_emojis(self) -> Iterator[tuple[int, int, str, type]]:
        """Check for emojis in code."""
        for i, line in enumerate(self.lines, 1):
            matches = EMOJI_PATTERN.findall(line)
            if matches:
                if self._should_ignore(i, "SLOP022"):
                    continue

                first_match = EMOJI_PATTERN.search(line)
                col = first_match.start() if first_match else 0

                yield (
                    i,
                    col,
                    f"SLOP022 Emoji detected: {' '.join(matches)}. Keep code professional.",
                    type(self),
                )
