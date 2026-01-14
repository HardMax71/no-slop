from typing import Callable


# =============================================================================
# Test: Line-level noqa ignores
# =============================================================================


def test_emoji_ignored() -> None:
    """This emoji should be ignored."""
    x = 1  # 🎉 noqa: SLP022


def test_emoji_not_ignored() -> None:
    """This emoji should NOT be ignored (wrong code)."""
    x = 1  # 🚀 noqa: SLP021


def test_all_ignored_on_line() -> None:
    """All checks ignored on this line."""
    x = 1  # ╔═══╗ 🎯 noqa


# =============================================================================
# Test: ASCII art ignores
# =============================================================================

# ╔════════════════════════════════════════╗  # noqa: SLP021
# ║  This box art is intentionally ignored ║  # noqa: SLP021
# ╚════════════════════════════════════════╝  # noqa: SLP021

# This one is NOT ignored:
# ████████████████████████████████


# =============================================================================
# Test: Multiple codes in noqa
# =============================================================================


def multi_ignore() -> None:
    x = "test"  # 🎉 ╔══╗ noqa: SLP021, SLP022


# =============================================================================
# Test: mypy plugin ignores (use type: ignore)
# =============================================================================

from dataclasses import dataclass


@dataclass
class User:
    name: str
    email: str


def test_mypy_ignore_hasattr(user: User) -> str:
    # Redundant hasattr - ignored with type: ignore
    if hasattr(user, "name"):  # type: ignore[slop-hasattr]
        return user.name
    return ""


def test_mypy_ignore_getattr(user: User) -> str:
    # Redundant getattr - ignored with type: ignore
    return getattr(user, "email", "none")  # type: ignore[slop-getattr]


def test_mypy_ignore_any_check(data: object) -> None:
    # hasattr on object type - ignored
    if hasattr(data, "x"):  # type: ignore[slop-any-check]
        pass


def test_mypy_ignore_callable(func: Callable[[], int]) -> int:
    # Redundant callable check - ignored
    if callable(func):  # type: ignore[slop-callable]
        return func()
    return 0  # type: ignore[unreachable]
