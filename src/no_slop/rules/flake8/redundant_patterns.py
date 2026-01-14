"""Detect redundant code patterns common in AI-generated code.

These patterns are syntactically valid but indicate unnecessary complexity
or defensive programming that obscures intent.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator

from no_slop.rules.flake8.base import IgnoreHandler

# Error codes for redundant patterns
SLP501 = "SLP501 Unnecessary else after return/raise/break/continue"
SLP502_TRUE = "SLP502 Redundant comparison: use 'if x' instead of 'if x == True'"
SLP502_FALSE = "SLP502 Redundant comparison: use 'if not x' instead of 'if x == False'"
SLP502_NONE = (
    "SLP502 Redundant comparison: use 'if x is None' instead of 'if x == None'"
)
SLP502_NOT_NONE = (
    "SLP502 Redundant comparison: use 'if x is not None' instead of 'if x != None'"
)
SLP502_LEN_ZERO = (
    "SLP502 Redundant comparison: use 'if not x' instead of 'if len(x) == 0'"
)
SLP502_LEN_NONZERO = (
    "SLP502 Redundant comparison: use 'if x' instead of 'if len(x) > 0'"
)
SLP503 = "SLP503 Unnecessary pass statement in non-empty block"
SLP504_BARE = (
    "SLP504 Bare except clause catches all exceptions including KeyboardInterrupt"
)
SLP504_SWALLOW = "SLP504 Exception swallowed with 'except Exception: pass'"
SLP505 = (
    "SLP505 Mutable default argument '{arg}={default}'. Use None and initialize in body"
)
SLP506 = "SLP506 f-string has no placeholders. Use regular string instead"
SLP507_LIST = "SLP507 Redundant list() call. '{arg}' is already a list"
SLP507_DICT = "SLP507 Redundant dict() call. Use dict literal {{}} instead"
SLP507_SET = "SLP507 Redundant set() call. Use set literal {{}} for non-empty sets"
SLP508 = "SLP508 Unnecessary .keys() in iteration. Use 'for k in d' instead"
SLP509 = "SLP509 Explicit 'return None' at end of function is redundant"
SLP510 = "SLP510 Use isinstance(x, {type_name}) instead of type(x) == {type_name}"


def _ends_with_jump(stmts: list[ast.stmt]) -> bool:
    """Check if a statement list ends with a control flow jump."""
    if not stmts:
        return False
    last = stmts[-1]
    if isinstance(last, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
        return True
    # Handle nested if that definitely jumps
    if isinstance(last, ast.If):
        if last.orelse:
            return _ends_with_jump(last.body) and _ends_with_jump(last.orelse)
    return False


def _is_pass_only(stmts: list[ast.stmt]) -> bool:
    """Check if statement list is only pass statements."""
    return all(isinstance(s, ast.Pass) for s in stmts)


def _get_type_name(node: ast.expr) -> str | None:
    """Extract type name from a node if it's a simple name."""
    if isinstance(node, ast.Name):
        return node.id
    return None  # noqa: SLP509


class RedundantPatternVisitor(ast.NodeVisitor):
    """Visitor that detects various redundant code patterns."""

    def __init__(self, ignore_handler: IgnoreHandler) -> None:
        self.errors: list[tuple[int, int, str]] = []
        self.ignore_handler = ignore_handler
        # Track function context for return None check
        self._in_function: list[ast.FunctionDef | ast.AsyncFunctionDef] = []

    def _add_error(self, node: ast.AST, code: str, message: str) -> None:
        """Add an error if not ignored."""
        lineno = getattr(node, "lineno", 0)
        col_offset = getattr(node, "col_offset", 0)
        if not self.ignore_handler.should_ignore(lineno, code):
            self.errors.append((lineno, col_offset, message))

    # SLP501: Unnecessary else after return/raise/break/continue
    def visit_If(self, node: ast.If) -> None:
        if node.orelse and _ends_with_jump(node.body):
            # Check it's not an elif
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                # This is elif, check recursively but don't flag here
                pass
            # Don't flag if else block is just a single jump statement
            # (e.g., if x: return 1 else: return 0 - this is a valid pattern)
            elif _ends_with_jump(node.orelse) and len(node.orelse) == 1:
                # Single return/raise/etc in else - valid pattern
                pass
            else:
                # Else block has multiple statements or doesn't end with jump
                # Report on the If node line for noqa to work on 'else:' line
                self._add_error(node, "SLP501", SLP501)

        self.generic_visit(node)

    # SLP502: Redundant boolean comparisons
    def visit_Compare(self, node: ast.Compare) -> None:
        # Only check single comparisons
        if len(node.ops) == 1 and len(node.comparators) == 1:
            op = node.ops[0]
            right = node.comparators[0]

            # x == True or x == False
            if isinstance(op, ast.Eq):
                if isinstance(right, ast.Constant):
                    if right.value is True:
                        self._add_error(node, "SLP502", SLP502_TRUE)
                    elif right.value is False:
                        self._add_error(node, "SLP502", SLP502_FALSE)
                    elif right.value is None:
                        self._add_error(node, "SLP502", SLP502_NONE)

            # x != None
            elif isinstance(op, ast.NotEq):
                if isinstance(right, ast.Constant) and right.value is None:
                    self._add_error(node, "SLP502", SLP502_NOT_NONE)

            # len(x) == 0 or len(x) > 0
            if isinstance(node.left, ast.Call):
                func = node.left.func
                if isinstance(func, ast.Name) and func.id == "len":
                    if isinstance(right, ast.Constant) and right.value == 0:
                        if isinstance(op, ast.Eq):
                            self._add_error(node, "SLP502", SLP502_LEN_ZERO)
                        elif isinstance(op, ast.Gt):
                            self._add_error(node, "SLP502", SLP502_LEN_NONZERO)

        self.generic_visit(node)

    # SLP503: Unnecessary pass in non-empty block
    def _check_pass_in_block(
        self, stmts: list[ast.stmt], block_type: str = "block"
    ) -> None:
        """Check for unnecessary pass statements in a block."""
        if len(stmts) > 1:
            for stmt in stmts:
                if isinstance(stmt, ast.Pass):
                    self._add_error(stmt, "SLP503", SLP503)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_pass_in_block(node.body)
        self._check_mutable_defaults(node)
        self._in_function.append(node)
        self.generic_visit(node)
        self._in_function.pop()
        self._check_return_none(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_pass_in_block(node.body)
        self._check_mutable_defaults(node)
        self._in_function.append(node)
        self.generic_visit(node)
        self._in_function.pop()
        self._check_return_none(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._check_pass_in_block(node.body)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._check_pass_in_block(node.body)
        self._check_pass_in_block(node.orelse)
        self._check_keys_iteration(node)
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._check_pass_in_block(node.body)
        self._check_pass_in_block(node.orelse)
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self._check_pass_in_block(node.body)
        self._check_pass_in_block(node.orelse)
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self._check_pass_in_block(node.body)
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self._check_pass_in_block(node.body)
        self.generic_visit(node)

    # SLP504: Bare except and exception swallowing
    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        # Bare except
        if node.type is None:
            self._add_error(node, "SLP504", SLP504_BARE)
        # except Exception: pass
        elif (
            isinstance(node.type, ast.Name)
            and node.type.id == "Exception"
            and _is_pass_only(node.body)
        ):
            self._add_error(node, "SLP504", SLP504_SWALLOW)

        self._check_pass_in_block(node.body)
        self.generic_visit(node)

    # SLP505: Mutable default arguments
    def _check_mutable_defaults(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        """Check for mutable default arguments."""
        defaults = node.args.defaults + node.args.kw_defaults
        args = node.args.args[-len(node.args.defaults) :] if node.args.defaults else []
        args += node.args.kwonlyargs

        for i, default in enumerate(defaults):
            if default is None:
                continue

            arg_name = args[i].arg if i < len(args) else "arg"
            default_repr = None

            if isinstance(default, ast.List):
                default_repr = "[]"
            elif isinstance(default, ast.Dict):
                default_repr = "{}"
            elif isinstance(default, ast.Set):
                default_repr = "set()"
            elif isinstance(default, ast.Call):
                func = default.func
                if isinstance(func, ast.Name) and func.id in ("list", "dict", "set"):
                    default_repr = f"{func.id}()"

            if default_repr:
                msg = SLP505.format(arg=arg_name, default=default_repr)
                self._add_error(default, "SLP505", msg)

    # SLP506: f-string with no placeholders
    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        # f-string with no FormattedValue nodes is just a string
        has_placeholder = any(isinstance(v, ast.FormattedValue) for v in node.values)
        if not has_placeholder:
            self._add_error(node, "SLP506", SLP506)
        self.generic_visit(node)

    # SLP507: Redundant list/dict/set wrapping
    # SLP508: Unnecessary .keys() in iteration
    # SLP510: type(x) == T instead of isinstance
    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            func_name = node.func.id

            # SLP507: list([...]) or list() without args
            if func_name == "list":
                if not node.args and not node.keywords:
                    # list() - should use []
                    self._add_error(node, "SLP507", SLP507_LIST.format(arg="[]"))
                elif len(node.args) == 1 and isinstance(node.args[0], ast.List):
                    self._add_error(node, "SLP507", SLP507_LIST.format(arg="[...]"))

            # SLP507: dict({...}) or dict() without args
            elif func_name == "dict":
                if not node.args and not node.keywords:
                    self._add_error(node, "SLP507", SLP507_DICT)
                elif (
                    len(node.args) == 1
                    and isinstance(node.args[0], ast.Dict)
                    and not node.keywords
                ):
                    self._add_error(node, "SLP507", SLP507_DICT)

            # SLP507: set() without args
            elif func_name == "set":
                if not node.args and not node.keywords:
                    # set() is valid for empty set, but often redundant
                    # Only flag if there's a set literal nearby... skip for now
                    pass

            # SLP510: type(x) == SomeType
            elif func_name == "type" and len(node.args) == 1:
                # This is handled in visit_Compare
                pass

        self.generic_visit(node)

    def _check_keys_iteration(self, node: ast.For) -> None:
        """Check for unnecessary .keys() in for loop iteration."""
        # for k in d.keys(): -> for k in d:
        iter_node = node.iter
        if isinstance(iter_node, ast.Call):
            if isinstance(iter_node.func, ast.Attribute):
                if (
                    iter_node.func.attr == "keys"
                    and not iter_node.args
                    and not iter_node.keywords
                ):
                    self._add_error(iter_node, "SLP508", SLP508)

    # SLP509: Explicit return None at end of function
    def _check_return_none(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Check for explicit return None at end of function."""
        if not node.body:
            return

        last_stmt = node.body[-1]
        if isinstance(last_stmt, ast.Return):
            # return None or return (no value defaults to None)
            if last_stmt.value is None:
                self._add_error(last_stmt, "SLP509", SLP509)
            elif (
                isinstance(last_stmt.value, ast.Constant)
                and last_stmt.value.value is None
            ):
                self._add_error(last_stmt, "SLP509", SLP509)

    # SLP510: type(x) == T instead of isinstance
    def _check_type_comparison(self, node: ast.Compare) -> None:
        """Check for type(x) == T patterns."""
        if len(node.ops) != 1 or len(node.comparators) != 1:
            return

        op = node.ops[0]
        if not isinstance(op, (ast.Eq, ast.Is)):
            return

        # Check left side is type() call
        left = node.left
        right = node.comparators[0]

        def is_type_call(n: ast.expr) -> bool:
            return (
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)
                and n.func.id == "type"
                and len(n.args) == 1
            )

        type_name = None
        if is_type_call(left):
            type_name = _get_type_name(right)
        elif is_type_call(right):
            type_name = _get_type_name(left)

        if type_name:
            msg = SLP510.format(type_name=type_name)
            self._add_error(node, "SLP510", msg)

    def visit_Compare_type_check(self, node: ast.Compare) -> None:
        """Additional check for type() comparisons."""
        self._check_type_comparison(node)


class TypeComparisonVisitor(ast.NodeVisitor):
    """Separate visitor for type comparison checks to avoid method override issues."""

    def __init__(self, ignore_handler: IgnoreHandler) -> None:
        self.errors: list[tuple[int, int, str]] = []
        self.ignore_handler = ignore_handler

    def _add_error(self, node: ast.expr | ast.stmt, code: str, message: str) -> None:
        if not self.ignore_handler.should_ignore(node.lineno, code):
            self.errors.append((node.lineno, node.col_offset, message))

    def visit_Compare(self, node: ast.Compare) -> None:
        if len(node.ops) != 1 or len(node.comparators) != 1:
            self.generic_visit(node)
            return

        op = node.ops[0]
        if not isinstance(op, (ast.Eq, ast.Is)):
            self.generic_visit(node)
            return

        left = node.left
        right = node.comparators[0]

        def is_type_call(n: ast.expr) -> bool:
            return (
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)
                and n.func.id == "type"
                and len(n.args) == 1
            )

        type_name = None
        if is_type_call(left):
            type_name = _get_type_name(right)
        elif is_type_call(right):
            type_name = _get_type_name(left)

        if type_name:
            msg = SLP510.format(type_name=type_name)
            self._add_error(node, "SLP510", msg)

        self.generic_visit(node)


def check_redundant_patterns(
    tree: ast.AST,
    ignore_handler: IgnoreHandler,
    checker_type: type,
) -> Iterator[tuple[int, int, str, type]]:
    """Check for redundant code patterns.

    Yields:
        Tuples of (line, column, message, checker_type) for each violation.
    """
    visitor = RedundantPatternVisitor(ignore_handler)
    visitor.visit(tree)
    for line, col, message in visitor.errors:
        yield (line, col, message, checker_type)

    # Run type comparison visitor separately
    type_visitor = TypeComparisonVisitor(ignore_handler)
    type_visitor.visit(tree)
    for line, col, message in type_visitor.errors:
        yield (line, col, message, checker_type)
