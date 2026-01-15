from __future__ import annotations

import ast

from .constants import UNION_TYPE_NAMES
from .indices import TypeIndex


def _annotation_type_key(node: ast.expr, type_index: TypeIndex) -> str | None:
    name = _annotation_type_name(node)
    if name is None:
        return None
    return type_index.resolve(name)


def _annotation_type_name(node: ast.expr) -> str | None:
    match node:
        case ast.Name(id=name):
            return name
        case ast.Attribute(attr=attr):
            return attr
        case ast.Subscript(value=value, slice=slice_):
            base = _annotation_type_name(value)
            if base in UNION_TYPE_NAMES:
                return _union_type_name(slice_)
            if base is not None:
                return base
            return None
        case ast.BinOp(left=left, op=ast.BitOr(), right=right):
            return _union_type_name(ast.Tuple(elts=[left, right], ctx=ast.Load()))
        case ast.Tuple():
            return _union_type_name(node)
    return None


def _union_type_name(node: ast.expr) -> str | None:
    match node:
        case ast.Tuple(elts=elts):
            elements = elts
        case _:
            elements = [node]
    names = {n for elt in elements if (n := _annotation_type_name(elt))}
    if len(names) == 1:
        return next(iter(names))
    return None


def _annotation_type_from_str(type_comment: str, type_index: TypeIndex) -> str | None:
    try:
        expr = ast.parse(type_comment, mode="eval").body
    except SyntaxError:
        return None
    return _annotation_type_key(expr, type_index)
