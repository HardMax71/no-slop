from __future__ import annotations

import ast
import re
from collections.abc import Iterator

from no_slop.rules.flake8.base import IgnoreHandler

# SLP030: Conversational residue patterns
CONVERSATIONAL_PATTERNS = [
    re.compile(r"^\s*#\s*(vbnet|javascript|python|cpp|csharp|java)\s*$", re.IGNORECASE),  # Language hints
    re.compile(r"here is the (updated |corrected )?code", re.IGNORECASE),
    re.compile(r"sure,? (here is|i can)", re.IGNORECASE),
    re.compile(r"as an ai", re.IGNORECASE),
    re.compile(r"i have (added|updated|fixed|implemented)", re.IGNORECASE),
    re.compile(r"hope this helps", re.IGNORECASE),
    re.compile(r"let me know if", re.IGNORECASE),
    re.compile(r"implementation of the .* function", re.IGNORECASE),
]

# SLP031: Obvious comments patterns mapping (Comment Text -> Code Start)
OBVIOUS_COMMENTS = {
    r"^imports?$": ("import ", "from "),
    r"^import (modules|libraries|packages)$": ("import ", "from "),
    r"^define (function|method)$": ("def ", "async def "),
    r"^define class$": ("class ",),
    r"^main function$": ("if __name__",),
    r"^variables?$": ("",),  # Too broad, but often precedes var declarations
    r"^constants?$": ("",),
    r"^return value$": ("return",),
    r"^increment (counter|i|index)$": ("i +=", "index +=", "counter +="),
}


# SLP032: Generic variable names to flag in function signatures
GENERIC_NAMES = {"data", "res", "val", "item", "obj", "content", "info", "result"}


def check_conversational_residue(
    lines: list[str],
    ignores: IgnoreHandler,
    checker_type: type,
) -> Iterator[tuple[int, int, str, type]]:
    """Detect conversational filler from LLM responses."""
    for i, line in enumerate(lines, 1):
        if not line.strip().startswith("#"):
            continue

        # Check for conversational patterns
        for pattern in CONVERSATIONAL_PATTERNS:
            if pattern.search(line):
                if ignores.should_ignore(i, "SLP030"):
                    break

                yield (
                    i,
                    0,
                    f"SLP030 Conversational detected: '{pattern.pattern}'. Remove chat residue.",
                    checker_type,
                )
                break


def check_obvious_comments(
    lines: list[str],
    ignores: IgnoreHandler,
    checker_type: type,
) -> Iterator[tuple[int, int, str, type]]:
    """Detect comments that explain the obvious syntax."""
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue

        comment_content = stripped.lstrip("# ").lower()

        # Check if next line exists and matches expectation
        if i + 1 >= len(lines):
            continue

        next_line = lines[i + 1].strip()
        if not next_line:
            continue

        for pattern, code_starts in OBVIOUS_COMMENTS.items():
            if re.search(pattern, comment_content):
                # If code matches one of the expected starts
                if any(next_line.startswith(start) for start in code_starts):
                    # Check ignore on comment line (i+1) or code line (i+2)
                    if ignores.should_ignore(i + 1, "SLP031") or ignores.should_ignore(i + 2, "SLP031"):
                        break

                    yield (
                        i + 1,
                        0,
                        f"SLP031 Obvious comment detected: '{stripped}'. Explain 'why', not 'what'.",
                        checker_type,
                    )
                    break


class GenericNameVisitor(ast.NodeVisitor):
    def __init__(self, ignore_handler: IgnoreHandler) -> None:
        self.errors: list[tuple[int, int, str]] = []
        self.ignore_handler = ignore_handler

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        args = node.args.args + node.args.posonlyargs + node.args.kwonlyargs
        for arg in args:
            if arg.arg in GENERIC_NAMES:
                if not self.ignore_handler.should_ignore(node.lineno, "SLP032"):
                    self.errors.append(
                        (
                            arg.lineno,
                            arg.col_offset,
                            f"SLP032 Generic argument name '{arg.arg}'. Use a descriptive name.",
                        )
                    )
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)


def check_generic_names(
    tree: ast.AST,
    ignores: IgnoreHandler,
    checker_type: type,
) -> Iterator[tuple[int, int, str, type]]:
    """Detect generic variable names in function signatures."""
    visitor = GenericNameVisitor(ignores)
    visitor.visit(tree)
    for line, col, message in visitor.errors:
        yield (line, col, message, checker_type)
