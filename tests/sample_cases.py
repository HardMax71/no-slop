"""
Test cases demonstrating AI-slop patterns that no-slop should detect.
Run mypy with the no_slop_plugin to see errors.
"""

from typing import Callable, Optional
from dataclasses import dataclass


@dataclass
class User:
    name: str
    email: str
    age: int


# =============================================================================
# SLOP001: Redundant isinstance
# =============================================================================


def process_user_bad(user: User) -> str:
    # BAD: isinstance check is redundant - user is always User
    if isinstance(user, User):
        return user.name
    return ""


def process_user_good(user: User) -> str:
    # GOOD: No redundant check
    return user.name


def process_number_bad(x: int) -> int:
    # BAD: x is always int
    if isinstance(x, int):
        return x * 2
    return 0


def process_union_ok(x: int | str) -> str:
    # OK: This is valid narrowing for a union type
    if isinstance(x, int):
        return str(x)
    return x


# =============================================================================
# SLOP003: Redundant hasattr
# =============================================================================


def get_user_name_bad(user: User) -> str:
    # BAD: User always has .name attribute
    if hasattr(user, "name"):
        return user.name
    return "unknown"


def get_user_name_good(user: User) -> str:
    # GOOD: Direct access
    return user.name


# =============================================================================
# SLOP004: Redundant getattr with default
# =============================================================================


def get_email_bad(user: User) -> str:
    # BAD: User always has .email, default is never used
    return getattr(user, "email", "no-email")


def get_email_good(user: User) -> str:
    # GOOD: Direct access
    return user.email


# =============================================================================
# SLOP005: Redundant callable
# =============================================================================


def invoke_bad(func: Callable[[], int]) -> int:
    # BAD: func is typed as Callable, check is redundant
    if callable(func):
        return func()
    return 0


def invoke_good(func: Callable[[], int]) -> int:
    # GOOD: Direct call
    return func()


# =============================================================================
# SLOP006: Redundant type() check
# =============================================================================


def check_exact_type_bad(x: int) -> bool:
    # BAD: x is exactly int
    return type(x) is int


def check_exact_type_ok(x: int | bool) -> bool:
    # OK: bool is subtype of int, so type check distinguishes them
    return type(x) is int


# =============================================================================
# SLOP010: Unused default parameters
# =============================================================================


def format_message(text: str, prefix: str = "[INFO]") -> str:
    """Default is used - this is fine."""
    return f"{prefix} {text}"


def process_data(data: list[int], multiplier: int = 1) -> list[int]:
    """
    BAD example - if ALL call sites always pass multiplier,
    the default is dead code.
    """
    return [x * multiplier for x in data]


# Simulate call sites that ALWAYS provide the argument
_r1 = process_data([1, 2, 3], 2)
_r2 = process_data([4, 5], 3)
_r3 = process_data([], 1)
# No call uses the default!


def calculate(a: int, b: int, c: int = 0) -> int:
    """Another case where default might be unused."""
    return a + b + c


# All calls provide c explicitly
_c1 = calculate(1, 2, 3)
_c2 = calculate(4, 5, 6)
_c3 = calculate(7, 8, 9)


# =============================================================================
# SLOP010: Optional[T] = None where None is never passed
# =============================================================================


def get_config(path: str, fallback: Optional[str] = None) -> str:
    """
    If ALL call sites pass a fallback value and never pass None,
    the Optional + default is unnecessary.
    """
    if fallback is None:
        return f"default:{path}"
    return fallback


# All calls provide explicit fallback
_g1 = get_config("/etc/app.conf", "/etc/default.conf")
_g2 = get_config("/home/user/.config", "/etc/app.conf")
# No call uses the default None!


# =============================================================================
# Valid patterns (should NOT be flagged)
# =============================================================================


def valid_default_usage(x: int, y: int = 10) -> int:
    """Default IS used by some call sites."""
    return x + y


# Mix of calls - some use default
_v1 = valid_default_usage(5)  # Uses default
_v2 = valid_default_usage(3, 20)  # Provides explicit


def dynamic_attr_access(obj: object, attr: str) -> object:
    """getattr with dynamic attr name - cannot analyze statically."""
    return getattr(obj, attr, None)


# =============================================================================
# SLOP007: Runtime checks on Any/untyped values
# =============================================================================


def process_untyped(data):  # No type annotation!
    """BAD: Using isinstance to compensate for missing types."""
    if isinstance(data, dict):
        return data.get("key")
    return None


def process_any(data: object) -> str:  # 'object' is effectively untyped
    """BAD: Using hasattr on object type."""
    if hasattr(data, "name"):
        return getattr(data, "name", "")
    return ""


def call_maybe(func: object) -> int:
    """BAD: callable() check on object type."""
    if callable(func):
        return func()
    return 0


# Good alternative:
def process_typed(data: dict[str, str]) -> str | None:
    """GOOD: Properly typed, no runtime check needed."""
    return data.get("key")


# =============================================================================
# SLOP008: Missing return type annotations
# =============================================================================


def no_return_type(x: int):  # Missing -> ...
    """BAD: Missing return type annotation."""
    return x * 2


def has_return_type(x: int) -> int:
    """GOOD: Has return type."""
    return x * 2
