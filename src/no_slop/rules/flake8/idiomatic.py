from __future__ import annotations

import ast
from collections.abc import Iterator

from no_slop.rules.flake8.base import IgnoreHandler

SLP601 = "SLP601 Redundant loop guarding: 'if {name}: for ... in {name}:' is redundant"
SLP602 = "SLP602 Unpythonic loop: Use 'for item in {name}:' or 'enumerate({name})'"


class IdiomaticVisitor(ast.NodeVisitor):
    def __init__(self, ignore_handler: IgnoreHandler) -> None:
        self.errors: list[tuple[int, int, str]] = []
        self.ignore_handler = ignore_handler

    def _add_error(self, node: ast.AST, code: str, message: str) -> None:
        if not self.ignore_handler.should_ignore(node.lineno, code):
            self.errors.append((node.lineno, node.col_offset, message))

    def visit_If(self, node: ast.If) -> None:
        # Check for SLP601: if x: for ... in x:
        if len(node.body) == 1 and isinstance(node.body[0], (ast.For, ast.AsyncFor)):
            for_node = node.body[0]

            # Extract names
            if_test_name = self._get_name(node.test)
            for_iter_name = self._get_name(for_node.iter)

            if if_test_name and for_iter_name and if_test_name == for_iter_name:
                # Ensure no else block
                if not node.orelse:
                    self._add_error(
                        node, "SLP601", SLP601.format(name=if_test_name)
                    )

        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._check_range_len(node)
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        # range(len()) is rarely used in async for, but logic holds if it were
        self.generic_visit(node)

    def _check_range_len(self, node: ast.For) -> None:
        # Check for SLP602: for i in range(len(x)):
        # iter must be range(len(x))
        if not (isinstance(node.iter, ast.Call) and
                isinstance(node.iter.func, ast.Name) and
                node.iter.func.id == "range"):
            return

        # Check range args
        if len(node.iter.args) != 1:
            return

        arg = node.iter.args[0]
        if not (isinstance(arg, ast.Call) and
                isinstance(arg.func, ast.Name) and
                arg.func.id == "len"):
            return

        if len(arg.args) != 1:
            return

        collection_name = self._get_name(arg.args[0])
        if not collection_name:
            return

        # Check loop var is a simple name
        loop_var = self._get_name(node.target)
        if not loop_var:
            return

        # Now check if we are doing `x[i]` inside the body
        # We want to flag if we see explicit indexing
        # Logic: UsageVisitor to find Subscript(x, i)
        usage_visitor = IndexingVisitor(collection_name, loop_var)
        for stmt in node.body:
            usage_visitor.visit(stmt)

        if usage_visitor.found_indexing:
            self._add_error(
                node, "SLP602", SLP602.format(name=collection_name)
            )

    def _get_name(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        return None


class IndexingVisitor(ast.NodeVisitor):
    def __init__(self, collection_name: str, index_name: str) -> None:
        self.collection_name = collection_name
        self.index_name = index_name
        self.found_indexing = False

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if self.found_indexing:
            return

        # Check for collection[index]
        if (isinstance(node.value, ast.Name) and
            node.value.id == self.collection_name):

            # Handle slice (Python < 3.9 uses ast.Index, 3.9+ uses explicit node)
            slice_node = node.slice
            # Simple check for direct name usage
            if isinstance(slice_node, ast.Name) and slice_node.id == self.index_name:
                self.found_indexing = True

        self.generic_visit(node)


def check_idiomatic_patterns(
    tree: ast.AST,
    ignore_handler: IgnoreHandler,
    checker_type: type,
) -> Iterator[tuple[int, int, str, type]]:
    """Check for non-idiomatic/redundant coding patterns."""
    visitor = IdiomaticVisitor(ignore_handler)
    visitor.visit(tree)
    for line, col, message in visitor.errors:
        yield (line, col, message, checker_type)
