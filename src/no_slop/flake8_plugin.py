from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from no_slop._version import __version__
from no_slop.rules.flake8 import (
    IgnoreHandler,
    check_ascii_art,
    check_emojis,
    check_leading_comments,
    check_local_imports,
    check_module_docstring,
)

if TYPE_CHECKING:
    from collections.abc import Generator

__all__ = ["SlopStyleChecker"]


class SlopStyleChecker:
    name = "no-slop"
    version = __version__

    def __init__(self, tree: ast.Module, lines: list[str], filename: str = "stdin"):
        self.tree = tree
        self.lines = lines
        self.filename = filename
        self._ignores = IgnoreHandler(lines)

    def run(self) -> Generator[tuple[int, int, str, type], None, None]:
        yield from check_module_docstring(self.tree, self._ignores, type(self))
        yield from check_leading_comments(self.lines, self._ignores, type(self))
        yield from check_ascii_art(self.lines, self._ignores, type(self))
        yield from check_emojis(self.lines, self._ignores, type(self))
        yield from check_local_imports(self.tree, self.lines, self._ignores, type(self))
