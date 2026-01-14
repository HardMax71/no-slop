from __future__ import annotations

from collections.abc import Callable

from mypy.errorcodes import ErrorCode
from mypy.nodes import Expression, RefExpr, StrExpr, TupleExpr
from mypy.plugin import FunctionContext, Plugin
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

__all__ = ["NoSlopPlugin", "plugin"]

# Error codes
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


def _is_any_or_untyped(typ: ProperType) -> bool:
    """Check if type is Any or effectively untyped (object)."""
    if isinstance(typ, AnyType):
        return True
    if isinstance(typ, Instance) and typ.type.fullname == "builtins.object":
        return True
    return False


def _is_proper_subtype(left: ProperType, right: ProperType) -> bool:
    """Check if left is always a subtype of right."""
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
        return all(_is_proper_subtype(get_proper_type(m), right) for m in left.items)

    if isinstance(left, NoneType) and isinstance(right, NoneType):
        return True

    return False


def _type_has_attribute(typ: ProperType, attr: str) -> bool | None:
    """Check if type definitely has an attribute. Returns None if uncertain."""
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
        results = [_type_has_attribute(get_proper_type(m), attr) for m in typ.items]
        if all(r is True for r in results):
            return True
        if any(r is None for r in results):
            return None
        return False

    return None


def _is_callable_type(typ: ProperType) -> bool | None:
    """Check if type is definitely callable."""
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
        results = [_is_callable_type(get_proper_type(m)) for m in typ.items]
        if all(r is True for r in results):
            return True
        if any(r is None for r in results):
            return None
        return False

    return None


def _type_to_str(typ: ProperType) -> str:
    """Convert type to readable string."""
    if isinstance(typ, Instance):
        return typ.type.name
    if isinstance(typ, UnionType):
        return " | ".join(_type_to_str(get_proper_type(m)) for m in typ.items)
    if isinstance(typ, NoneType):
        return "None"
    if isinstance(typ, CallableType):
        return "Callable"
    if isinstance(typ, AnyType):
        return "Any"
    return str(typ)


class NoSlopPlugin(Plugin):
    """Mypy plugin to detect redundant reflection patterns."""

    def get_function_hook(
        self, fullname: str
    ) -> Callable[[FunctionContext], Type] | None:
        hooks = {
            "builtins.isinstance": self._check_isinstance,
            "builtins.issubclass": self._check_issubclass,
            "builtins.hasattr": self._check_hasattr,
            "builtins.getattr": self._check_getattr,
            "builtins.callable": self._check_callable,
        }
        return hooks.get(fullname)

    def _check_isinstance(self, ctx: FunctionContext) -> Type:
        if len(ctx.args) < 2 or not ctx.args[0] or not ctx.args[1]:
            return ctx.default_return_type

        obj_type = get_proper_type(ctx.api.get_expression_type(ctx.args[0][0]))

        if _is_any_or_untyped(obj_type):
            ctx.api.fail(
                "[SLOP007] isinstance on Any/untyped value. "
                "Add type annotation to parameter instead of runtime check.",
                ctx.context,
                code=SLOP_RUNTIME_CHECK_ON_ANY,
            )
            return ctx.default_return_type

        check_types = self._extract_isinstance_types(ctx.args[1][0], ctx)
        for check_type in check_types:
            check_proper = get_proper_type(check_type)
            if _is_proper_subtype(obj_type, check_proper):
                ctx.api.fail(
                    f"[SLOP001] Redundant isinstance: '{_type_to_str(obj_type)}' "
                    f"is always instance of '{_type_to_str(check_proper)}'. Remove check.",
                    ctx.context,
                    code=SLOP_REDUNDANT_ISINSTANCE,
                )
                break

        return ctx.default_return_type

    def _check_issubclass(self, ctx: FunctionContext) -> Type:
        if len(ctx.args) < 2 or not ctx.args[0] or not ctx.args[1]:
            return ctx.default_return_type

        cls_type = get_proper_type(ctx.api.get_expression_type(ctx.args[0][0]))

        if _is_any_or_untyped(cls_type):
            ctx.api.fail(
                "[SLOP007] issubclass on Any/untyped value. "
                "Add type annotation instead of runtime check.",
                ctx.context,
                code=SLOP_RUNTIME_CHECK_ON_ANY,
            )
            return ctx.default_return_type

        # Extract the inner type from type[X] or Type[X]
        inner_type: ProperType | None = None

        if isinstance(cls_type, TypeType) and cls_type.item:
            inner_type = get_proper_type(cls_type.item)
        elif isinstance(cls_type, Instance):
            if cls_type.type.fullname == "builtins.type" and cls_type.args:
                inner_type = get_proper_type(cls_type.args[0])

        if inner_type is None:
            return ctx.default_return_type

        check_types = self._extract_isinstance_types(ctx.args[1][0], ctx)

        for check_type in check_types:
            check_proper = get_proper_type(check_type)
            if _is_proper_subtype(inner_type, check_proper):
                ctx.api.fail(
                    f"[SLOP002] Redundant issubclass: '{_type_to_str(inner_type)}' "
                    f"is always subclass of '{_type_to_str(check_proper)}'. Remove check.",
                    ctx.context,
                    code=SLOP_REDUNDANT_ISSUBCLASS,
                )
                break

        return ctx.default_return_type

    def _check_hasattr(self, ctx: FunctionContext) -> Type:
        if len(ctx.args) < 2 or not ctx.args[0] or not ctx.args[1]:
            return ctx.default_return_type

        attr_expr = ctx.args[1][0]
        if not isinstance(attr_expr, StrExpr):
            return ctx.default_return_type

        obj_type = get_proper_type(ctx.api.get_expression_type(ctx.args[0][0]))

        if _is_any_or_untyped(obj_type):
            ctx.api.fail(
                "[SLOP007] hasattr on Any/untyped value. "
                "Add type annotation instead of runtime check.",
                ctx.context,
                code=SLOP_RUNTIME_CHECK_ON_ANY,
            )
            return ctx.default_return_type

        if _type_has_attribute(obj_type, attr_expr.value) is True:
            ctx.api.fail(
                f"[SLOP003] Redundant hasattr: '{_type_to_str(obj_type)}' always has "
                f"attribute '{attr_expr.value}'. Use obj.{attr_expr.value} directly.",
                ctx.context,
                code=SLOP_REDUNDANT_HASATTR,
            )

        return ctx.default_return_type

    def _check_getattr(self, ctx: FunctionContext) -> Type:
        if len(ctx.args) < 2 or not ctx.args[0] or not ctx.args[1]:
            return ctx.default_return_type

        attr_expr = ctx.args[1][0]
        if not isinstance(attr_expr, StrExpr):
            return ctx.default_return_type

        obj_type = get_proper_type(ctx.api.get_expression_type(ctx.args[0][0]))

        if _is_any_or_untyped(obj_type):
            ctx.api.fail(
                "[SLOP007] getattr on Any/untyped value. "
                "Add type annotation instead of runtime check.",
                ctx.context,
                code=SLOP_RUNTIME_CHECK_ON_ANY,
            )
            return ctx.default_return_type

        # Only warn if there's a default (3rd arg)
        if _type_has_attribute(obj_type, attr_expr.value) is True:
            if len(ctx.args) >= 3 and ctx.args[2]:
                ctx.api.fail(
                    f"[SLOP004] Redundant getattr with default: '{_type_to_str(obj_type)}' "
                    f"always has '{attr_expr.value}'. Use obj.{attr_expr.value} directly.",
                    ctx.context,
                    code=SLOP_REDUNDANT_GETATTR,
                )

        return ctx.default_return_type

    def _check_callable(self, ctx: FunctionContext) -> Type:
        if len(ctx.args) < 1 or not ctx.args[0]:
            return ctx.default_return_type

        obj_type = get_proper_type(ctx.api.get_expression_type(ctx.args[0][0]))

        if _is_any_or_untyped(obj_type):
            ctx.api.fail(
                "[SLOP007] callable() on Any/untyped value. "
                "Add Callable type annotation instead of runtime check.",
                ctx.context,
                code=SLOP_RUNTIME_CHECK_ON_ANY,
            )
            return ctx.default_return_type

        if _is_callable_type(obj_type) is True:
            ctx.api.fail(
                f"[SLOP005] Redundant callable: '{_type_to_str(obj_type)}' is statically "
                "callable. Remove check.",
                ctx.context,
                code=SLOP_REDUNDANT_CALLABLE,
            )

        return ctx.default_return_type

    def _extract_isinstance_types(
        self, expr: Expression, ctx: FunctionContext
    ) -> list[Type]:
        types: list[Type] = []
        if isinstance(expr, TupleExpr):
            for item in expr.items:
                types.extend(self._extract_isinstance_types(item, ctx))
        elif isinstance(expr, RefExpr):
            typ = ctx.api.get_expression_type(expr)
            if typ:
                proper = get_proper_type(typ)
                extracted = self._extract_class_type(proper)
                if extracted:
                    types.append(extracted)
                else:
                    types.append(typ)
        return types

    def _extract_class_type(self, typ: ProperType) -> Type | None:
        """Extract the instance type from a class reference."""
        # Handle type[X] case (explicit Type annotation)
        if (
            isinstance(typ, Instance)
            and typ.type.fullname == "builtins.type"
            and typ.args
        ):
            return typ.args[0]

        # Handle TypeType[X]
        if isinstance(typ, TypeType) and typ.item:
            return typ.item

        # Handle class reference (callable constructor)
        if isinstance(typ, CallableType) and typ.ret_type:
            ret = get_proper_type(typ.ret_type)
            if isinstance(ret, Instance):
                return ret

        # Handle overloaded constructors (like int, str, etc.)
        if isinstance(typ, Overloaded) and typ.items:
            # Take the return type from the first overload
            first = typ.items[0]
            if first.ret_type:
                ret = get_proper_type(first.ret_type)
                if isinstance(ret, Instance):
                    return ret

        return None


def plugin(version: str) -> type[NoSlopPlugin]:
    """Entry point for mypy plugin."""
    return NoSlopPlugin
