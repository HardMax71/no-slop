from __future__ import annotations

from collections.abc import Callable

from mypy.plugin import FunctionContext, Plugin
from mypy.types import Type

from no_slop.rules.mypy import (
    check_callable,
    check_getattr,
    check_hasattr,
    check_isinstance,
    check_issubclass,
)

__all__ = ["NoSlopPlugin", "plugin"]


class NoSlopPlugin(Plugin):
    def get_function_hook(
        self, fullname: str
    ) -> Callable[[FunctionContext], Type] | None:
        hooks = {
            "builtins.isinstance": check_isinstance,
            "builtins.issubclass": check_issubclass,
            "builtins.hasattr": check_hasattr,
            "builtins.getattr": check_getattr,
            "builtins.callable": check_callable,
        }
        return hooks.get(fullname)


def plugin(version: str) -> type[NoSlopPlugin]:
    return NoSlopPlugin
