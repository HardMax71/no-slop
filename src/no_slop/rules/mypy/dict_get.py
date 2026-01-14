from __future__ import annotations

from mypy.nodes import StrExpr
from mypy.plugin import MethodContext
from mypy.types import Type, TypedDictType, get_proper_type

from no_slop.rules.mypy.base import SLOP_REDUNDANT_DICT_GET


def check_typed_dict_get(ctx: MethodContext) -> Type:
    """Check for redundant .get() calls on TypedDict required keys."""
    obj_type = get_proper_type(ctx.type)

    if not isinstance(obj_type, TypedDictType):
        return ctx.default_return_type

    # Need at least one argument (the key)
    if not ctx.args or not ctx.args[0]:
        return ctx.default_return_type

    key_expr = ctx.args[0][0]
    if not isinstance(key_expr, StrExpr):
        return ctx.default_return_type

    key = key_expr.value

    # Check if key is in required_keys and has a default argument
    if key in obj_type.required_keys:
        has_default = len(ctx.args) > 1 and ctx.args[1]
        if has_default:
            ctx.api.fail(
                f"Redundant .get() with default: TypedDict key '{key}' "
                f"is required. Use obj['{key}'] directly.",
                ctx.context,
                code=SLOP_REDUNDANT_DICT_GET,
            )

    return ctx.default_return_type
