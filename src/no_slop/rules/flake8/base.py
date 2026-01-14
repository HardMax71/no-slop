from __future__ import annotations

import re

NOQA_PATTERN = re.compile(r"#.*\bnoqa\b(?::\s*([A-Z0-9,\s]+))?", re.IGNORECASE)
FILE_IGNORE_PATTERN = re.compile(
    r"#\s*slop:\s*ignore-file(?:\[([A-Z0-9,\s]+)\])?", re.IGNORECASE
)

MAX_LEADING_COMMENT_LINES = 10
MAX_DOCSTRING_LINES_ABSOLUTE = 15

MAX_MODULE_DOCSTRING_LINES = 5
MAX_DOCSTRING_CODE_RATIO = 0.3


class IgnoreHandler:
    def __init__(self, lines: list[str]):
        self._file_ignores: set[str] = set()
        self._line_ignores: dict[int, set[str]] = {}
        self._parse_ignores(lines)

    def _parse_ignores(self, lines: list[str]) -> None:
        for i, line in enumerate(lines, 1):
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

    def should_ignore(self, line: int, code: str) -> bool:
        code = code.upper()
        if "*" in self._file_ignores or code in self._file_ignores:
            return True
        if line in self._line_ignores:
            ignores = self._line_ignores[line]
            if "*" in ignores or code in ignores:
                return True
        return False
