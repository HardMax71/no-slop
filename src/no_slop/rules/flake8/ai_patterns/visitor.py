from __future__ import annotations

import ast
import os

from no_slop.rules.flake8.base import IgnoreHandler

from .annotations import _annotation_type_from_str, _annotation_type_key
from .ast_utils import (
    _base_names,
    _docstring_node,
    _function_length,
    _has_abstract_decorator,
    _is_placeholder_stmt,
    _is_type_checking_test,
    _max_nesting_depth,
    _node_end_line,
    _strip_docstring,
)
from .constants import (
    CROSS_LANGUAGE_ATTRS,
    DEBUG_ATTR_CALLS,
    DEBUG_CALLS,
    HEDGE_PATTERN,
    MAX_FUNCTION_LINES,
    MAX_NESTING_DEPTH,
    SLP033,
    SLP035,
    SLP036,
    SLP037,
    SLP038,
    SLP039,
    SLP040,
)
from .indices import ModuleIndex, TypeIndex


def _is_test_path(filename: str) -> bool:
    normalized = filename.replace("\\", "/")
    if "/tests/" in normalized or normalized.startswith("tests/"):
        return True
    base = os.path.basename(normalized)
    return base.startswith("test_") or base.endswith("_test.py")


class AIPatternVisitor(ast.NodeVisitor):
    def __init__(
        self,
        ignore_handler: IgnoreHandler,
        filename: str,
        module_index: ModuleIndex,
        type_index: TypeIndex,
    ) -> None:
        self.errors: list[tuple[int, int, str]] = []
        self.ignore_handler = ignore_handler
        self._class_stack: list[bool] = []
        self._import_guard_depth = 0
        self._type_checking_depth = 0
        self._debug_guard_depth = 0
        self._skip_debug_artifacts = _is_test_path(filename)
        self._call_attr_nodes: set[int] = set()
        self._module_index = module_index
        self._type_index = type_index
        self._annotation_scopes: list[dict[str, str]] = [{}]
        self.placeholder_header_lines: set[int] = set()
        self.placeholder_ranges: list[tuple[int, int]] = []

    def _add_error(self, node: ast.stmt | ast.expr, code: str, message: str) -> None:
        if not self.ignore_handler.should_ignore(node.lineno, code):
            self.errors.append((node.lineno, node.col_offset, message))

    def visit_Module(self, node: ast.Module) -> None:
        self._check_docstring_hedging(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._check_docstring_hedging(node)
        is_abstract_or_protocol = bool(_base_names(node) & {"ABC", "Protocol"})
        self._class_stack.append(is_abstract_or_protocol)
        self._annotation_scopes.append({})
        if self._is_placeholder_class(node):
            self._add_error(node, "SLP033", SLP033)
            self._record_placeholder_node(node)
        if self._is_single_method_wrapper(node):
            self._add_error(node, "SLP039", SLP039)
        self.generic_visit(node)
        self._annotation_scopes.pop()
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_docstring_hedging(node)
        if self._is_placeholder_function(node):
            self._add_error(node, "SLP033", SLP033)
            self._record_placeholder_node(node)
        self._check_function_complexity(node)
        self._annotation_scopes.append({})
        self._record_function_annotations(node)
        self.generic_visit(node)
        self._annotation_scopes.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_docstring_hedging(node)
        if self._is_placeholder_function(node):
            self._add_error(node, "SLP033", SLP033)
            self._record_placeholder_node(node)
        self._check_function_complexity(node)
        self._annotation_scopes.append({})
        self._record_function_annotations(node)
        self.generic_visit(node)
        self._annotation_scopes.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        if node.type_comment:
            kind = _annotation_type_from_str(node.type_comment, self._type_index)
            if kind:
                for target in node.targets:
                    self._record_annotation_target(target, kind)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        kind = _annotation_type_key(node.annotation, self._type_index)
        if kind:
            self._record_annotation_target(node.target, kind)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        match node.func:
            case ast.Attribute() as attr:
                self._call_attr_nodes.add(id(attr))
                self._check_cross_language(attr)
                self._check_debug_attr_call(attr, node)
            case ast.Name() as name:
                self._check_debug_call(name, node)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if id(node) not in self._call_attr_nodes:
            self._check_cross_language(node)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        if self._import_guard_depth or self._type_checking_depth:
            return
        for alias in node.names:
            if not self._is_module_resolvable(alias.name):
                self._add_error(node, "SLP037", SLP037.format(module=alias.name))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if self._import_guard_depth or self._type_checking_depth:
            return
        if node.level and node.level > 0:
            return
        if not node.module:
            return
        if not self._is_module_resolvable(node.module):
            self._add_error(node, "SLP037", SLP037.format(module=node.module))

    def visit_If(self, node: ast.If) -> None:
        if _is_type_checking_test(node.test):
            self._type_checking_depth += 1
            for stmt in node.body:
                self.visit(stmt)
            self._type_checking_depth -= 1
            for stmt in node.orelse:
                self.visit(stmt)
            return
        match node.test:
            case ast.Name(id="__debug__"):
                self._debug_guard_depth += 1
                for stmt in node.body:
                    self.visit(stmt)
                self._debug_guard_depth -= 1
                for stmt in node.orelse:
                    self.visit(stmt)
                return
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        guarded = self._try_handles_import_error(node)
        if guarded:
            self._import_guard_depth += 1
        for stmt in node.body:
            self.visit(stmt)
        if guarded:
            self._import_guard_depth -= 1
        for handler in node.handlers:
            self.visit(handler)
        for stmt in node.orelse:
            self.visit(stmt)
        for stmt in node.finalbody:
            self.visit(stmt)

    def _check_docstring_hedging(self, node: ast.AST) -> None:
        doc_node = _docstring_node(node)
        if not doc_node:
            return
        match doc_node.value:
            case ast.Constant(value=str() as doc):
                pass
            case _:
                return
        if HEDGE_PATTERN.search(doc):
            if not self.ignore_handler.should_ignore(doc_node.lineno, "SLP038"):
                self.errors.append((doc_node.lineno, doc_node.col_offset, SLP038))

    def _is_placeholder_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> bool:
        if _has_abstract_decorator(node):
            return False
        if self._class_stack and self._class_stack[-1]:
            return False
        body = _strip_docstring(node.body)
        if not body:
            return False
        return all(_is_placeholder_stmt(stmt) for stmt in body)

    def _is_placeholder_class(self, node: ast.ClassDef) -> bool:
        if _base_names(node) & {"ABC", "Protocol"}:
            return False
        body = _strip_docstring(node.body)
        if not body:
            return False
        return all(_is_placeholder_stmt(stmt) for stmt in body)

    def _is_single_method_wrapper(self, node: ast.ClassDef) -> bool:
        if node.bases or node.decorator_list:
            return False
        body = _strip_docstring(node.body)
        if not body:
            return False
        methods: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
        for stmt in body:
            match stmt:
                case ast.FunctionDef() | ast.AsyncFunctionDef():
                    if stmt.decorator_list:
                        return False
                    methods.append(stmt)
                case _:
                    return False
        public_methods = [m for m in methods if not m.name.startswith("_")]
        if len(public_methods) != 1:
            return False
        public_name = public_methods[0].name
        for method in methods:
            if method.name not in {public_name, "__init__"}:
                return False
        return True

    def _check_function_complexity(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        max_depth = _max_nesting_depth(node.body)
        length = _function_length(node)
        if max_depth > MAX_NESTING_DEPTH:
            detail = f"nesting {max_depth} > {MAX_NESTING_DEPTH}"
            self._add_error(node, "SLP040", SLP040.format(detail=detail))
        elif length > MAX_FUNCTION_LINES:
            detail = f"length {length} lines > {MAX_FUNCTION_LINES}"
            self._add_error(node, "SLP040", SLP040.format(detail=detail))

    def _check_debug_call(self, func: ast.Name, node: ast.Call) -> None:
        if self._skip_debug_artifacts or self._debug_guard_depth:
            return
        if func.id in DEBUG_CALLS:
            self._add_error(node, "SLP035", SLP035)

    def _check_debug_attr_call(self, func: ast.Attribute, node: ast.Call) -> None:
        if self._skip_debug_artifacts or self._debug_guard_depth:
            return
        match func.value:
            case ast.Name(id=module):
                key = (module, func.attr)
                if key in DEBUG_ATTR_CALLS:
                    self._add_error(node, "SLP035", SLP035)

    def _check_cross_language(self, node: ast.Attribute) -> None:
        if node.attr not in CROSS_LANGUAGE_ATTRS:
            return
        value = node.value
        match value:
            case ast.Name(id=name):
                kind = self._lookup_annotation(name)
                if kind and not self._type_index.has_attr(kind, node.attr):
                    self._add_error(node, "SLP036", SLP036.format(attr=node.attr))
                    return
            case ast.List() | ast.Dict() | ast.Set():
                self._add_error(node, "SLP036", SLP036.format(attr=node.attr))
                return
            case ast.Constant(value=str()):
                self._add_error(node, "SLP036", SLP036.format(attr=node.attr))
                return
            case ast.Call(func=ast.Name(id=func_id)) if func_id in {
                "list",
                "dict",
                "set",
            }:
                self._add_error(node, "SLP036", SLP036.format(attr=node.attr))

    def _try_handles_import_error(self, node: ast.Try) -> bool:
        for handler in node.handlers:
            exc = handler.type
            match exc:
                case ast.Name(id=name) if name in {
                    "ImportError",
                    "ModuleNotFoundError",
                }:
                    return True
                case ast.Attribute(attr=attr) if attr in {
                    "ImportError",
                    "ModuleNotFoundError",
                }:
                    return True
        return False

    def _is_module_resolvable(self, module: str) -> bool:
        return self._module_index.is_known(module)

    def _record_annotation_target(self, target: ast.expr, kind: str) -> None:
        match target:
            case ast.Name(id=name):
                self._annotation_scopes[-1][name] = kind
            case ast.Tuple(elts=elts) | ast.List(elts=elts):
                for elt in elts:
                    self._record_annotation_target(elt, kind)

    def _record_placeholder_node(self, node: ast.stmt | ast.expr) -> None:
        start = node.lineno
        end = _node_end_line(node)
        self.placeholder_header_lines.add(start)
        self.placeholder_ranges.append((start, end))

    def _lookup_annotation(self, name: str) -> str | None:
        for scope in reversed(self._annotation_scopes):
            if name in scope:
                return scope[name]
        return None

    def _record_function_annotations(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        for arg in node.args.posonlyargs + node.args.args + node.args.kwonlyargs:
            if arg.annotation is None:
                continue
            kind = _annotation_type_key(arg.annotation, self._type_index)
            if kind:
                self._annotation_scopes[-1][arg.arg] = kind
        if node.args.vararg and node.args.vararg.annotation:
            kind = _annotation_type_key(node.args.vararg.annotation, self._type_index)
            if kind:
                self._annotation_scopes[-1][node.args.vararg.arg] = kind
        if node.args.kwarg and node.args.kwarg.annotation:
            kind = _annotation_type_key(node.args.kwarg.annotation, self._type_index)
            if kind:
                self._annotation_scopes[-1][node.args.kwarg.arg] = kind
