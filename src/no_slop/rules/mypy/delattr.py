from __future__ import annotations

from mypy.nodes import StrExpr
from mypy.plugin import FunctionContext
from mypy.types import Type, get_proper_type

from no_slop.rules.mypy.base import (
    SLOP_REDUNDANT_DELATTR,
    SLOP_RUNTIME_CHECK_ON_ANY,
    has_custom_delattr,
    is_any_or_untyped,
    type_has_attribute,
    type_to_str,
)


def check_delattr(ctx: FunctionContext) -> Type:
    """Check for redundant delattr() calls on known attributes."""
    if len(ctx.args) < 2 or not ctx.args[0] or not ctx.args[1]:
        return ctx.default_return_type

    attr_expr = ctx.args[1][0]
    if not isinstance(attr_expr, StrExpr):
        return ctx.default_return_type

    obj_type = get_proper_type(ctx.api.get_expression_type(ctx.args[0][0]))

    if is_any_or_untyped(obj_type):
        ctx.api.fail(
            "delattr on Any/untyped value. "
            "Add type annotation instead of runtime deletion.",
            ctx.context,
            code=SLOP_RUNTIME_CHECK_ON_ANY,
        )
        return ctx.default_return_type

    # Skip if class has custom __delattr__
    if has_custom_delattr(obj_type):
        return ctx.default_return_type

    if type_has_attribute(obj_type, attr_expr.value) is True:
        ctx.api.fail(
            f"Redundant delattr: '{type_to_str(obj_type)}' "
            f"has '{attr_expr.value}'. Use del obj.{attr_expr.value} directly.",
            ctx.context,
            code=SLOP_REDUNDANT_DELATTR,
        )

    return ctx.default_return_type
