from __future__ import annotations

from mypy.plugin import FunctionContext
from mypy.types import Type, get_proper_type

from no_slop.rules.mypy.base import (
    SLOP_REDUNDANT_CALLABLE,
    SLOP_RUNTIME_CHECK_ON_ANY,
    is_any_or_untyped,
    is_callable_type,
    type_to_str,
)


def check_callable(ctx: FunctionContext) -> Type:
    if len(ctx.args) < 1 or not ctx.args[0]:
        return ctx.default_return_type

    obj_type = get_proper_type(ctx.api.get_expression_type(ctx.args[0][0]))

    if is_any_or_untyped(obj_type):
        ctx.api.fail(
            "callable() on Any/untyped value. "
            "Add Callable type annotation instead of runtime check.",
            ctx.context,
            code=SLOP_RUNTIME_CHECK_ON_ANY,
        )
        return ctx.default_return_type

    if is_callable_type(obj_type) is True:
        ctx.api.fail(
            f"Redundant callable: '{type_to_str(obj_type)}' is statically "
            "callable. Remove check.",
            ctx.context,
            code=SLOP_REDUNDANT_CALLABLE,
        )

    return ctx.default_return_type
