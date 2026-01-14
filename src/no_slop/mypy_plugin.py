from __future__ import annotations

from collections.abc import Callable

from mypy.plugin import FunctionContext, MethodContext, Plugin
from mypy.types import Type

from no_slop.rules.mypy import (
    check_callable,
    check_delattr,
    check_getattr,
    check_hasattr,
    check_isinstance,
    check_issubclass,
    check_setattr,
    check_typed_dict_get,
)

__all__ = ["NoSlopPlugin", "plugin"]


class NoSlopPlugin(Plugin):
    def get_function_hook(
        self, fullname: str
    ) -> Callable[[FunctionContext], Type] | None:
        hooks: dict[str, Callable[[FunctionContext], Type]] = {
            "builtins.isinstance": check_isinstance,
            "builtins.issubclass": check_issubclass,
            "builtins.hasattr": check_hasattr,
            "builtins.getattr": check_getattr,
            "builtins.setattr": check_setattr,
            "builtins.delattr": check_delattr,
            "builtins.callable": check_callable,
        }
        return hooks.get(fullname)

    def get_method_hook(self, fullname: str) -> Callable[[MethodContext], Type] | None:
        # TypedDict.get() comes through as typing.Mapping.get
        if fullname == "typing.Mapping.get":
            return check_typed_dict_get
        return None  # noqa: SLP509


def plugin(version: str) -> type[NoSlopPlugin]:
    return NoSlopPlugin
