"""Detect indirect attribute access patterns that bypass direct obj.attr syntax.

These patterns are almost always AI slop - there's no good reason to use them
when direct attribute access is available.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator

from no_slop.rules.flake8.base import IgnoreHandler

# Error codes for indirect access patterns
SLP401 = "SLP401 Use obj.attr or getattr() instead of obj.__dict__.get()"
SLP402 = "SLP402 Use obj.attr instead of obj.__dict__[key]"
SLP403 = "SLP403 Use obj.attr = value instead of obj.__dict__[key] = value"
SLP404 = "SLP404 Use direct attribute assignment instead of obj.__dict__.update()"
SLP405 = "SLP405 Use obj.attr or getattr() instead of vars(obj).get()"
SLP406 = "SLP406 Use obj.attr = value instead of vars(obj)[key] = value"
SLP407 = "SLP407 Use obj.attr instead of asdict(obj).get()"
SLP408 = "SLP408 Key '{key}' defined in dict. Use d['{key}'] instead of .get()"


def _extract_dict_keys(node: ast.expr) -> set[str] | None:
    """Extract string keys from dict literal or dict() call.

    Returns None if keys cannot be determined statically (dynamic keys, **kwargs, etc.)
    """
    # Dict literal: {"a": 1, "b": 2}
    if isinstance(node, ast.Dict):
        keys: set[str] = set()
        for key in node.keys:
            if key is None:  # **spread operator
                return None
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                keys.add(key.value)
            else:
                return None  # Dynamic key
        return keys

    # dict() call
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "dict":
            keys = set()
            # Keyword arguments: dict(a=1, b=2)
            for kw in node.keywords:
                if kw.arg:  # Regular keyword
                    keys.add(kw.arg)
                else:  # **kwargs
                    return None
            # Positional argument: dict({"a": 1})
            if node.args:
                if len(node.args) == 1:
                    inner = _extract_dict_keys(node.args[0])
                    if inner is not None:
                        keys.update(inner)
                    else:
                        return None
                else:
                    return None  # Multiple args - can't analyze
            return keys

    return None  # noqa: SLP509


class IndirectAccessVisitor(ast.NodeVisitor):
    """Visitor that detects indirect attribute access patterns."""

    def __init__(self, ignore_handler: IgnoreHandler) -> None:
        self.errors: list[tuple[int, int, str]] = []
        self.ignore_handler = ignore_handler
        # Track asdict imports/aliases
        self.asdict_names: set[str] = {"asdict"}
        # Track dict variables with known keys: var_name -> set of keys
        self.known_dicts: dict[str, set[str]] = {}

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track imports of asdict to handle aliases."""
        if node.module == "dataclasses":
            for alias in node.names:
                if alias.name == "asdict":
                    # Use the alias name if provided, otherwise use "asdict"
                    self.asdict_names.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Track dict variable assignments for SLP408 detection."""
        # Only track simple assignments: var = dict(...) or var = {...}
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id
            keys = _extract_dict_keys(node.value)
            if keys is not None:
                self.known_dicts[var_name] = keys
            else:
                # Reassignment to non-trackable value - clear tracking
                self.known_dicts.pop(var_name, None)
        self.generic_visit(node)

    def visit_Delete(self, node: ast.Delete) -> None:
        """Handle del statements that might remove dict keys."""
        for target in node.targets:
            # del d["key"] - remove specific key from tracking
            if (
                isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Name)
                and isinstance(target.slice, ast.Constant)
                and isinstance(target.slice.value, str)
            ):
                var_name = target.value.id
                key = target.slice.value
                if var_name in self.known_dicts:
                    self.known_dicts[var_name].discard(key)
            # del d - clear tracking entirely
            elif isinstance(target, ast.Name):
                self.known_dicts.pop(target.id, None)
        self.generic_visit(node)

    def _add_error(self, node: ast.expr | ast.stmt, code: str, message: str) -> None:
        """Add an error if not ignored."""
        if not self.ignore_handler.should_ignore(node.lineno, code):
            self.errors.append((node.lineno, node.col_offset, message))

    def _is_dict_attr(self, node: ast.AST) -> bool:
        """Check if node is obj.__dict__"""
        return isinstance(node, ast.Attribute) and node.attr == "__dict__"

    def _is_vars_call(self, node: ast.AST) -> bool:
        """Check if node is vars(obj)"""
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "vars"
            and len(node.args) >= 1
        )

    def _is_asdict_call(self, node: ast.AST) -> bool:
        """Check if node is asdict(obj)"""
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in self.asdict_names
            and len(node.args) >= 1
        )

    def visit_Call(self, node: ast.Call) -> None:
        """Check for .get() and .update() calls on __dict__, vars(), asdict()."""
        if isinstance(node.func, ast.Attribute):
            method_name = node.func.attr
            obj = node.func.value

            # Check for .get() calls
            if method_name == "get" and node.args:
                # Check first arg is a string literal
                if isinstance(node.args[0], ast.Constant) and isinstance(
                    node.args[0].value, str
                ):
                    key = node.args[0].value
                    has_default = len(node.args) >= 2

                    # SLP401: obj.__dict__.get("attr", ...)
                    if self._is_dict_attr(obj):
                        self._add_error(node, "SLP401", SLP401)

                    # SLP405: vars(obj).get("attr", ...)
                    elif self._is_vars_call(obj):
                        self._add_error(node, "SLP405", SLP405)

                    # SLP407: asdict(obj).get("attr", ...)
                    elif self._is_asdict_call(obj):
                        self._add_error(node, "SLP407", SLP407)

                    # SLP408: Check for .get() on dict with known keys
                    elif has_default:
                        # Inline: dict(a=1).get("a", x) or {"a": 1}.get("a", x)
                        inline_keys = _extract_dict_keys(obj)
                        if inline_keys is not None and key in inline_keys:
                            msg = SLP408.format(key=key)
                            self._add_error(node, "SLP408", msg)

                        # Variable: d = dict(a=1); d.get("a", x)
                        elif isinstance(obj, ast.Name):
                            var_name = obj.id
                            if (
                                var_name in self.known_dicts
                                and key in self.known_dicts[var_name]
                            ):
                                msg = SLP408.format(key=key)
                                self._add_error(node, "SLP408", msg)

            # SLP404: obj.__dict__.update(...)
            elif method_name == "update" and self._is_dict_attr(obj):
                self._add_error(node, "SLP404", SLP404)

            # Track dict.pop() and dict.clear() to update known_dicts
            elif method_name == "pop" and isinstance(obj, ast.Name):
                var_name = obj.id
                if var_name in self.known_dicts and node.args:
                    if isinstance(node.args[0], ast.Constant) and isinstance(
                        node.args[0].value, str
                    ):
                        self.known_dicts[var_name].discard(node.args[0].value)

            elif method_name == "clear" and isinstance(obj, ast.Name):
                var_name = obj.id
                if var_name in self.known_dicts:
                    self.known_dicts[var_name].clear()

        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Check for subscript access on __dict__ and vars()."""
        # Only check if subscript key is a string literal
        if not (
            isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str)
        ):
            self.generic_visit(node)
            return

        obj = node.value

        # SLP402/SLP403: obj.__dict__["attr"] (read or write)
        if self._is_dict_attr(obj):
            # Check context to determine read vs write
            if isinstance(node.ctx, ast.Store):
                self._add_error(node, "SLP403", SLP403)
            elif isinstance(node.ctx, ast.Load):
                self._add_error(node, "SLP402", SLP402)

        # SLP406: vars(obj)["attr"] = value (write only - read is less common)
        elif self._is_vars_call(obj):
            if isinstance(node.ctx, ast.Store):
                self._add_error(node, "SLP406", SLP406)

        self.generic_visit(node)


def check_indirect_access(
    tree: ast.AST,
    ignore_handler: IgnoreHandler,
    checker_type: type,
) -> Iterator[tuple[int, int, str, type]]:
    """Check for indirect attribute access patterns.

    Yields:
        Tuples of (line, column, message, checker_type) for each violation.
    """
    visitor = IndirectAccessVisitor(ignore_handler)
    visitor.visit(tree)
    for line, col, message in visitor.errors:
        yield (line, col, message, checker_type)
