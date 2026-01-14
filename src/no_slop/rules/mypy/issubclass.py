from __future__ import annotations

from mypy.plugin import FunctionContext
from mypy.types import Instance, ProperType, Type, TypeType, get_proper_type

from no_slop.rules.mypy.base import (
    SLOP_REDUNDANT_ISSUBCLASS,
    SLOP_RUNTIME_CHECK_ON_ANY,
    extract_type_check_types,
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
            "issubclass on Any/untyped value. "
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

    check_types = extract_type_check_types(ctx.args[1][0], ctx)

    for check_type in check_types:
        check_proper = get_proper_type(check_type)
        if is_proper_subtype(inner_type, check_proper):
            ctx.api.fail(
                f"Redundant issubclass: '{type_to_str(inner_type)}' "
                f"is always subclass of '{type_to_str(check_proper)}'. Remove check.",
                ctx.context,
                code=SLOP_REDUNDANT_ISSUBCLASS,
            )
            break

    return ctx.default_return_type
