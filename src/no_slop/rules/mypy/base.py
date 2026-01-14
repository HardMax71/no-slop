from __future__ import annotations

from typing import TYPE_CHECKING

from mypy.errorcodes import ErrorCode
from mypy.nodes import Expression, RefExpr, TupleExpr
from mypy.types import (
    AnyType,
    CallableType,
    Instance,
    NoneType,
    Overloaded,
    ProperType,
    Type,
    TypeType,
    UnionType,
    get_proper_type,
)

if TYPE_CHECKING:
    from mypy.plugin import FunctionContext

SLOP_REDUNDANT_ISINSTANCE = ErrorCode(
    "slop-isinstance", "Redundant isinstance check", "General"
)
SLOP_REDUNDANT_HASATTR = ErrorCode("slop-hasattr", "Redundant hasattr check", "General")
SLOP_REDUNDANT_GETATTR = ErrorCode("slop-getattr", "Redundant getattr call", "General")
SLOP_REDUNDANT_CALLABLE = ErrorCode(
    "slop-callable", "Redundant callable check", "General"
)
SLOP_REDUNDANT_ISSUBCLASS = ErrorCode(
    "slop-issubclass", "Redundant issubclass check", "General"
)
SLOP_RUNTIME_CHECK_ON_ANY = ErrorCode(
    "slop-any-check",
    "Runtime check on Any/untyped - add type annotation instead",
    "General",
)


def is_any_or_untyped(typ: ProperType) -> bool:
    if isinstance(typ, AnyType):
        return True
    if isinstance(typ, Instance) and typ.type.fullname == "builtins.object":
        return True
    return False


def is_proper_subtype(left: ProperType, right: ProperType) -> bool:
    if isinstance(right, AnyType) or isinstance(left, AnyType):
        return False

    if isinstance(left, Instance) and isinstance(right, Instance):
        if left.type.fullname == right.type.fullname:
            return True
        for base in left.type.mro:
            if base.fullname == right.type.fullname:
                return True
        return False

    if isinstance(left, UnionType):
        return all(is_proper_subtype(get_proper_type(m), right) for m in left.items)

    if isinstance(left, NoneType) and isinstance(right, NoneType):
        return True

    return False


def type_has_attribute(typ: ProperType, attr: str) -> bool | None:
    if isinstance(typ, AnyType):
        return None

    if isinstance(typ, Instance):
        type_info = typ.type
        if type_info.get(attr) is not None:
            return True
        for base in type_info.mro:
            if base.get(attr) is not None:
                return True
        if type_info.get("__getattr__") is not None:
            return None
        return False

    if isinstance(typ, UnionType):
        results = [type_has_attribute(get_proper_type(m), attr) for m in typ.items]
        if all(r is True for r in results):
            return True
        if any(r is None for r in results):
            return None
        return False

    return None


def is_callable_type(typ: ProperType) -> bool | None:
    if isinstance(typ, AnyType):
        return None

    if isinstance(typ, CallableType):
        return True

    if isinstance(typ, Instance):
        type_info = typ.type
        if type_info.get("__call__") is not None:
            return True
        if type_info.is_metaclass():
            return True
        return False

    if isinstance(typ, UnionType):
        results = [is_callable_type(get_proper_type(m)) for m in typ.items]
        if all(r is True for r in results):
            return True
        if any(r is None for r in results):
            return None
        return False

    return None


def type_to_str(typ: ProperType) -> str:
    if isinstance(typ, Instance):
        return typ.type.name
    if isinstance(typ, UnionType):
        return " | ".join(type_to_str(get_proper_type(m)) for m in typ.items)
    if isinstance(typ, NoneType):
        return "None"
    if isinstance(typ, CallableType):
        return "Callable"
    if isinstance(typ, AnyType):
        return "Any"
    return str(typ)


def extract_type_check_types(expr: Expression, ctx: FunctionContext) -> list[Type]:
    """Extract types from isinstance/issubclass second argument (class or tuple of classes)."""
    types: list[Type] = []
    if isinstance(expr, TupleExpr):
        for item in expr.items:
            types.extend(extract_type_check_types(item, ctx))
    elif isinstance(expr, RefExpr):
        typ = ctx.api.get_expression_type(expr)
        if typ:
            proper = get_proper_type(typ)
            extracted = extract_class_type(proper)
            if extracted:
                types.append(extracted)
            else:
                types.append(typ)
    return types


def extract_class_type(typ: ProperType) -> Type | None:
    """Extract the class type from type[X], Type[X], or callable that returns X."""
    if isinstance(typ, Instance) and typ.type.fullname == "builtins.type" and typ.args:
        return typ.args[0]

    if isinstance(typ, TypeType) and typ.item:
        return typ.item

    if isinstance(typ, CallableType) and typ.ret_type:
        ret = get_proper_type(typ.ret_type)
        if isinstance(ret, Instance):
            return ret

    if isinstance(typ, Overloaded) and typ.items:
        first = typ.items[0]
        if first.ret_type:
            ret = get_proper_type(first.ret_type)
            if isinstance(ret, Instance):
                return ret

    return None
