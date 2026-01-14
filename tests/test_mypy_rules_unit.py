from __future__ import annotations

from mypy.options import Options
from mypy.types import AnyType, NoneType, TypeOfAny, UnboundType

from no_slop.mypy_plugin import NoSlopPlugin, plugin
from no_slop.rules.mypy.base import (
    is_any_or_untyped,
    is_callable_type,
    is_proper_subtype,
    type_has_attribute,
    type_to_str,
)


class TestIsAnyOrUntyped:
    def test_any_type(self) -> None:
        any_type = AnyType(TypeOfAny.unannotated)
        assert is_any_or_untyped(any_type) is True

    def test_none_type(self) -> None:
        none_type = NoneType()
        assert is_any_or_untyped(none_type) is False


class TestIsProperSubtype:
    def test_any_left(self) -> None:
        any_type = AnyType(TypeOfAny.unannotated)
        none_type = NoneType()
        assert is_proper_subtype(any_type, none_type) is False

    def test_any_right(self) -> None:
        any_type = AnyType(TypeOfAny.unannotated)
        none_type = NoneType()
        assert is_proper_subtype(none_type, any_type) is False

    def test_none_none(self) -> None:
        none1 = NoneType()
        none2 = NoneType()
        assert is_proper_subtype(none1, none2) is True


class TestTypeHasAttribute:
    def test_any_type_returns_none(self) -> None:
        any_type = AnyType(TypeOfAny.unannotated)
        assert type_has_attribute(any_type, "foo") is None

    def test_none_type_returns_none(self) -> None:
        none_type = NoneType()
        assert type_has_attribute(none_type, "foo") is None


class TestIsCallableType:
    def test_any_type_returns_none(self) -> None:
        any_type = AnyType(TypeOfAny.unannotated)
        assert is_callable_type(any_type) is None

    def test_none_type_returns_none(self) -> None:
        none_type = NoneType()
        assert is_callable_type(none_type) is None


class TestTypeToStr:
    def test_any_type(self) -> None:
        any_type = AnyType(TypeOfAny.unannotated)
        assert type_to_str(any_type) == "Any"

    def test_none_type(self) -> None:
        none_type = NoneType()
        assert type_to_str(none_type) == "None"

    def test_other_type(self) -> None:
        unbound = UnboundType("SomeType")
        result = type_to_str(unbound)
        assert "SomeType" in result


class TestEdgeCases:
    def test_is_proper_subtype_none_vs_any(self) -> None:
        none_type = NoneType()
        any_type = AnyType(TypeOfAny.unannotated)
        assert is_proper_subtype(none_type, any_type) is False

    def test_type_to_str_duplicate(self) -> None:
        result = type_to_str(NoneType())
        assert result == "None"


class TestMypyPlugin:
    def test_plugin_returns_class(self) -> None:
        result = plugin("1.0.0")
        assert result is NoSlopPlugin

    def test_get_function_hook_isinstance(self) -> None:
        p = NoSlopPlugin(Options())
        hook = p.get_function_hook("builtins.isinstance")
        assert hook is not None

    def test_get_function_hook_issubclass(self) -> None:
        p = NoSlopPlugin(Options())
        hook = p.get_function_hook("builtins.issubclass")
        assert hook is not None

    def test_get_function_hook_hasattr(self) -> None:
        p = NoSlopPlugin(Options())
        hook = p.get_function_hook("builtins.hasattr")
        assert hook is not None

    def test_get_function_hook_getattr(self) -> None:
        p = NoSlopPlugin(Options())
        hook = p.get_function_hook("builtins.getattr")
        assert hook is not None

    def test_get_function_hook_callable(self) -> None:
        p = NoSlopPlugin(Options())
        hook = p.get_function_hook("builtins.callable")
        assert hook is not None

    def test_get_function_hook_unknown(self) -> None:
        p = NoSlopPlugin(Options())
        hook = p.get_function_hook("builtins.len")
        assert hook is None
