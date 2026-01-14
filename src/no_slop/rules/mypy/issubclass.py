from __future__ import annotations

from mypy.nodes import Expression, RefExpr, TupleExpr
from mypy.plugin import FunctionContext
from mypy.types import (
    CallableType,
    Instance,
    Overloaded,
    ProperType,
    Type,
    TypeType,
    get_proper_type,
)

from no_slop.rules.mypy.base import (
    SLOP_REDUNDANT_ISSUBCLASS,
    SLOP_RUNTIME_CHECK_ON_ANY,
    is_any_or_untyped,
    is_proper_subtype,
    type_to_str,
)


def check_issubclass(ctx: FunctionContext) -> Type:
    if len(ctx.args) < 2 or not ctx.args[0] or not ctx.args[1]:
        return ctx.default_return_type

    cls_type = get_proper_type(ctx.api.get_expression_type(ctx.args[0][0]))

    if is_any_or_untyped(cls_type):
        ctx.api.fail(
            "[SLOP007] issubclass on Any/untyped value. "
            "Add type annotation instead of runtime check.",
            ctx.context,
            code=SLOP_RUNTIME_CHECK_ON_ANY,
        )
        return ctx.default_return_type

    inner_type: ProperType | None = None

    if isinstance(cls_type, TypeType) and cls_type.item:
        inner_type = get_proper_type(cls_type.item)
    elif isinstance(cls_type, Instance):
        if cls_type.type.fullname == "builtins.type" and cls_type.args:
            inner_type = get_proper_type(cls_type.args[0])

    if inner_type is None:
        return ctx.default_return_type

    check_types = _extract_isinstance_types(ctx.args[1][0], ctx)

    for check_type in check_types:
        check_proper = get_proper_type(check_type)
        if is_proper_subtype(inner_type, check_proper):
            ctx.api.fail(
                f"[SLOP002] Redundant issubclass: '{type_to_str(inner_type)}' "
                f"is always subclass of '{type_to_str(check_proper)}'. Remove check.",
                ctx.context,
                code=SLOP_REDUNDANT_ISSUBCLASS,
            )
            break

    return ctx.default_return_type


def _extract_isinstance_types(expr: Expression, ctx: FunctionContext) -> list[Type]:
    types: list[Type] = []
    if isinstance(expr, TupleExpr):
        for item in expr.items:
            types.extend(_extract_isinstance_types(item, ctx))
    elif isinstance(expr, RefExpr):
        typ = ctx.api.get_expression_type(expr)
        if typ:
            proper = get_proper_type(typ)
            extracted = _extract_class_type(proper)
            if extracted:
                types.append(extracted)
            else:
                types.append(typ)
    return types


def _extract_class_type(typ: ProperType) -> Type | None:
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
