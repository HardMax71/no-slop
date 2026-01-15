from __future__ import annotations

import ast
from collections.abc import Iterator

from no_slop.rules.flake8.base import IgnoreHandler

from .comments import check_hedging_comments, check_placeholder_comments
from .indices import _module_index, _type_index
from .visitor import AIPatternVisitor


def check_ai_patterns(
    tree: ast.AST,
    lines: list[str],
    ignores: IgnoreHandler,
    checker_type: type,
    filename: str,
) -> Iterator[tuple[int, int, str, type]]:
    """Detect AI-generated patterns not covered by standard linters."""
    module_index = _module_index()
    type_index = _type_index()
    visitor = AIPatternVisitor(ignores, filename, module_index, type_index)
    visitor.visit(tree)
    yield from check_placeholder_comments(
        lines,
        ignores,
        checker_type,
        visitor.placeholder_header_lines,
        visitor.placeholder_ranges,
    )
    yield from check_hedging_comments(lines, ignores, checker_type)
    for line, col, message in visitor.errors:
        yield (line, col, message, checker_type)
