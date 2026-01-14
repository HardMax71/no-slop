from __future__ import annotations

from mypy.plugin import FunctionContext
from mypy.types import Type, get_proper_type

from no_slop.rules.mypy.base import (
    SLOP_REDUNDANT_ISINSTANCE,
    SLOP_RUNTIME_CHECK_ON_ANY,
    extract_type_check_types,
    is_any_or_untyped,
    is_proper_subtype,
    type_to_str,
)


def check_isinstance(ctx: FunctionContext) -> Type:
    if len(ctx.args) < 2 or not ctx.args[0] or not ctx.args[1]:
        return ctx.default_return_type

    obj_type = get_proper_type(ctx.api.get_expression_type(ctx.args[0][0]))

    if is_any_or_untyped(obj_type):
        ctx.api.fail(
            "isinstance on Any/untyped value."
            "Add type annotation to parameter instead of runtime check.",
            ctx.context,
            code=SLOP_RUNTIME_CHECK_ON_ANY,
        )
        return ctx.default_return_type

    check_types = extract_type_check_types(ctx.args[1][0], ctx)
    for check_type in check_types:
        check_proper = get_proper_type(check_type)
        if is_proper_subtype(obj_type, check_proper):
            ctx.api.fail(
                f"Redundant isinstance: '{type_to_str(obj_type)}' "
                f"is always instance of '{type_to_str(check_proper)}'. Remove check.",
                ctx.context,
                code=SLOP_REDUNDANT_ISINSTANCE,
            )
            break

    return ctx.default_return_type
