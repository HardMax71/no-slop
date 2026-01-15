from __future__ import annotations

import ast
import builtins


def _docstring_node(node: ast.AST) -> ast.Expr | None:
    match node:
        case (
            ast.Module(body=body)
            | ast.FunctionDef(body=body)
            | ast.AsyncFunctionDef(body=body)
            | ast.ClassDef(body=body)
        ):
            if not body:
                return None
            match body[0]:
                case ast.Expr(value=ast.Constant(value=str())):
                    return body[0]
            return None
    return None


def _strip_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    if not body:
        return body
    match body[0]:
        case ast.Expr(value=ast.Constant(value=str())):
            return body[1:]
    return body


def _is_placeholder_stmt(stmt: ast.stmt) -> bool:
    match stmt:
        case ast.Pass():
            return True
        case ast.Expr(value=ast.Constant(value=builtins.Ellipsis)):
            return True
        case ast.Raise(exc=exc):
            match exc:
                case ast.Name(id="NotImplementedError"):
                    return True
                case ast.Attribute(attr="NotImplementedError"):
                    return True
                case ast.Call(func=ast.Name(id="NotImplementedError")):
                    return True
                case ast.Call(func=ast.Attribute(attr="NotImplementedError")):
                    return True
    return False


def _has_abstract_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for dec in node.decorator_list:
        match dec:
            case ast.Name(id=name) if name in {
                "abstractmethod",
                "abstractproperty",
                "abstractclassmethod",
                "abstractstaticmethod",
            }:
                return True
            case ast.Attribute(attr=attr) if attr in {
                "abstractmethod",
                "abstractproperty",
                "abstractclassmethod",
                "abstractstaticmethod",
            }:
                return True
    return False


def _base_names(node: ast.ClassDef) -> set[str]:
    names: set[str] = set()
    for base in node.bases:
        match base:
            case ast.Name(id=name):
                names.add(name)
            case ast.Attribute(attr=attr):
                names.add(attr)
    return names


def _is_type_checking_test(test: ast.AST) -> bool:
    match test:
        case ast.Name(id="TYPE_CHECKING") | ast.Attribute(attr="TYPE_CHECKING"):
            return True
    return False


def _function_length(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    if node.end_lineno is not None:
        return node.end_lineno - node.lineno + 1
    end = node.lineno
    for child in ast.walk(node):
        match child:
            case ast.stmt() | ast.expr():
                child_end = (
                    child.end_lineno if child.end_lineno is not None else child.lineno
                )
                end = max(end, child_end)
    return end - node.lineno + 1


def _node_end_line(node: ast.stmt | ast.expr) -> int:
    if node.end_lineno is not None:
        return node.end_lineno
    end = node.lineno
    for child in ast.walk(node):
        match child:
            case ast.stmt() | ast.expr():
                child_end = (
                    child.end_lineno if child.end_lineno is not None else child.lineno
                )
                end = max(end, child_end)
    return end


def _max_nesting_depth(stmts: list[ast.stmt], depth: int = 0) -> int:
    max_depth = depth
    for stmt in stmts:
        match stmt:
            case ast.FunctionDef() | ast.AsyncFunctionDef() | ast.ClassDef():
                continue
            case (
                ast.If()
                | ast.For()
                | ast.AsyncFor()
                | ast.While()
                | ast.Try()
                | ast.With()
                | ast.AsyncWith()
                | ast.Match()
            ):
                next_depth = depth + 1
                max_depth = max(max_depth, next_depth)
                for block in _iter_child_blocks(stmt):
                    max_depth = max(max_depth, _max_nesting_depth(block, next_depth))
    return max_depth


def _iter_child_blocks(stmt: ast.stmt) -> list[list[ast.stmt]]:
    match stmt:
        case ast.If(body=body, orelse=orelse):
            return [body, orelse]
        case ast.For(body=body, orelse=orelse) | ast.AsyncFor(body=body, orelse=orelse):
            return [body, orelse]
        case ast.While(body=body, orelse=orelse):
            return [body, orelse]
        case ast.Try(body=body, orelse=orelse, finalbody=finalbody, handlers=handlers):
            blocks = [body, orelse, finalbody]
            blocks.extend(handler.body for handler in handlers)
            return blocks
        case ast.With(body=body) | ast.AsyncWith(body=body):
            return [body]
        case ast.Match(cases=cases):
            return [case.body for case in cases]
    return []
