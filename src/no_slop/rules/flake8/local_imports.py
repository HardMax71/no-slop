from __future__ import annotations

import ast
from collections.abc import Iterator

from no_slop.rules.flake8.base import IgnoreHandler


class LocalImportVisitor(ast.NodeVisitor):
    def __init__(
        self,
        ignores: IgnoreHandler,
        checker_type: type,
    ):
        self.ignores = ignores
        self.checker_type = checker_type
        self.errors: list[tuple[int, int, str, type]] = []
        self._in_function = False
        self._in_type_checking = False

    def visit_If(self, node: ast.If) -> None:
        if self._is_type_checking_block(node):
            old_in_type_checking = self._in_type_checking
            self._in_type_checking = True
            self.generic_visit(node)
            self._in_type_checking = old_in_type_checking
        else:
            self.generic_visit(node)

    def _is_type_checking_block(self, node: ast.If) -> bool:
        test = node.test
        if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
            return True
        if isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING":
            return True
        return False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        old_in_function = self._in_function
        self._in_function = True
        self.generic_visit(node)
        self._in_function = old_in_function

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        old_in_function = self._in_function
        self._in_function = True
        self.generic_visit(node)
        self._in_function = old_in_function

    def visit_Import(self, node: ast.Import) -> None:
        if self._in_function and not self._in_type_checking:
            if not self.ignores.should_ignore(node.lineno, "SLP023"):
                names = ", ".join(alias.name for alias in node.names)
                self.errors.append(
                    (
                        node.lineno,
                        node.col_offset,
                        f"SLP023 Local import '{names}'. Move to module level.",
                        self.checker_type,
                    )
                )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if self._in_function and not self._in_type_checking:
            if not self.ignores.should_ignore(node.lineno, "SLP023"):
                module = node.module or ""
                names = ", ".join(alias.name for alias in node.names)
                self.errors.append(
                    (
                        node.lineno,
                        node.col_offset,
                        f"SLP023 Local import 'from {module} import {names}'. "
                        "Move to module level.",
                        self.checker_type,
                    )
                )


def check_local_imports(
    tree: ast.Module,
    lines: list[str],  # noqa: ARG001 - kept for API compatibility
    ignores: IgnoreHandler,
    checker_type: type,
) -> Iterator[tuple[int, int, str, type]]:
    visitor = LocalImportVisitor(ignores, checker_type)
    visitor.visit(tree)
    yield from visitor.errors
