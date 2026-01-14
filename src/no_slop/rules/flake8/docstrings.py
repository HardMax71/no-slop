from __future__ import annotations

import ast
from collections.abc import Iterator

from no_slop.rules.flake8.base import (
    MAX_DOCSTRING_CODE_RATIO,
    MAX_DOCSTRING_LINES_ABSOLUTE,
    MAX_LEADING_COMMENT_LINES,
    MAX_MODULE_DOCSTRING_LINES,
    IgnoreHandler,
)


def check_module_docstring(
    tree: ast.Module,
    ignores: IgnoreHandler,
    checker_type: type,
) -> Iterator[tuple[int, int, str, type]]:
    if not tree.body:
        return

    first_node = tree.body[0]
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
    for node in tree.body[1:]:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            code_lines += (node.end_lineno or node.lineno) - node.lineno + 1
        elif not isinstance(node, ast.Expr):
            code_lines += 1

    if code_lines > 0:
        ratio = doc_line_count / max(code_lines, 1)
        if (
            ratio > MAX_DOCSTRING_CODE_RATIO
            or doc_line_count > MAX_DOCSTRING_LINES_ABSOLUTE
        ):
            if not ignores.should_ignore(first_node.lineno, "SLP020"):
                yield (
                    first_node.lineno,
                    0,
                    f"SLP020 Excessive module docstring ({doc_line_count} lines). "
                    "Keep docs near the code they document.",
                    checker_type,
                )


def check_leading_comments(
    lines: list[str],
    ignores: IgnoreHandler,
    checker_type: type,
) -> Iterator[tuple[int, int, str, type]]:
    comment_lines = 0
    first_comment_line = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            if first_comment_line is None:
                first_comment_line = i + 1
            comment_lines += 1
        elif stripped == "":
            continue
        else:
            break

    if comment_lines > MAX_LEADING_COMMENT_LINES and first_comment_line is not None:
        if not ignores.should_ignore(first_comment_line, "SLP020"):
            yield (
                first_comment_line,
                0,
                f"SLP020 Excessive leading comment block ({comment_lines} lines). "
                "Keep docs near the code they document.",
                checker_type,
            )
