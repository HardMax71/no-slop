# no-slop

Detect AI-generated code patterns via static analysis.

## Overview

`no-slop` is a collection of linting tools that detect common patterns often found in AI-generated code:

- **Redundant runtime type checks** when static types already guarantee the result
- **Runtime checks on untyped values** where type annotations should be added instead
- **Stylistic patterns** like ASCII art, emojis, and excessive docstrings
- **Unused default parameters** where all call sites provide explicit values

## Installation

```bash
pip install no-slop
```

Or with uv:

```bash
uv add no-slop
```

## Components

### 1. mypy Plugin (Type-based checks)

Detects redundant reflection patterns that indicate runtime checks where static typing already provides guarantees.

**Error codes:**

| Code | Description |
|------|-------------|
| `slop-isinstance` | `isinstance(x, T)` when `x: T` is already guaranteed |
| `slop-issubclass` | `issubclass(C, T)` when `C` is already a subclass of `T` |
| `slop-hasattr` | `hasattr(obj, "attr")` when type guarantees attr exists |
| `slop-getattr` | `getattr(obj, "attr", default)` when type guarantees attr exists |
| `slop-callable` | `callable(f)` when `f` is typed as `Callable` |
| `slop-any-check` | Any reflection on `Any`/`object`/untyped values |

**Configuration:**

```toml
# pyproject.toml
[tool.mypy]
plugins = ["no_slop.mypy_plugin"]
```

Or in `mypy.ini`:

```ini
[mypy]
plugins = no_slop.mypy_plugin
```

**Example detections:**

```python
from dataclasses import dataclass

@dataclass
class User:
    name: str
    email: str

def process(user: User) -> str:
    # SLOP001: Redundant isinstance - user is always User
    if isinstance(user, User):
        return user.name
    return ""

def get_name(user: User) -> str:
    # SLOP003: Redundant hasattr - User always has 'name'
    if hasattr(user, "name"):
        return user.name
    return ""

def get_email(user: User) -> str:
    # SLOP004: Redundant getattr - User always has 'email'
    return getattr(user, "email", "none")

def invoke(func: Callable[[], int]) -> int:
    # SLOP005: Redundant callable - func is Callable
    if callable(func):
        return func()
    return 0

def bad_pattern(data):  # No type annotation!
    # SLOP007: isinstance on untyped value - add annotation instead
    if isinstance(data, dict):
        return data.get("key")
```

**Ignoring errors:**

```python
if hasattr(user, "name"):  # type: ignore[slop-hasattr]
    ...
```

### 2. flake8 Plugin (Style checks)

Detects stylistic patterns commonly found in AI-generated code.

**Error codes:**

| Code | Description |
|------|-------------|
| `SLOP020` | Excessive module docstring or leading comment block |
| `SLOP021` | ASCII art (box drawing, block characters) |
| `SLOP022` | Emojis in code |

**Usage:**

The flake8 plugin auto-registers when `no-slop` is installed:

```bash
flake8 your_project/
```

**Ignoring errors:**

```python
# Line-level ignore
x = "hello"  # noqa: SLOP022

# Ignore multiple codes
x = "test"  # noqa: SLOP021, SLOP022

# Ignore all slop checks on line
x = "test"  # noqa

# File-level ignore (in first 10 lines)
# slop: ignore-file
# slop: ignore-file[SLOP021, SLOP022]
```

### 3. Unused Defaults CLI (Whole-program analysis)

Detects function parameters with default values that are never used across the entire codebase.

```bash
no-slop-unused-defaults /path/to/project
no-slop-unused-defaults . --json
no-slop-unused-defaults . --min-calls 3
```

**Example:**

```python
# lib.py
def process(data: list[int], multiplier: int = 1) -> list[int]:
    return [x * multiplier for x in data]

# main.py - ALL calls provide explicit multiplier
result1 = process([1, 2, 3], 2)
result2 = process([4, 5], 3)
result3 = process([], 1)
# The default value `1` is dead code!
```

Output:
```
lib.py:2:44: SLOP010
  Function: process
  Parameter: multiplier = 1
  Default '1' for 'multiplier' is never used (3 call sites)
```

## Development

```bash
# Clone and install
git clone https://github.com/yourname/no-slop
cd no-slop
uv venv
uv pip install -e ".[dev]"

# Run tests
uv run pytest

# Run linters
uv run mypy src/no_slop --strict
uv run ruff check src/no_slop tests/
uv run ruff format src/no_slop tests/
```

## Philosophy

AI-generated code often includes defensive patterns that make sense when types are unknown, but become redundant when proper type annotations exist:

1. **Trust your types**: If mypy passes, you don't need `isinstance` checks
2. **Type, don't check**: Instead of `if hasattr(obj, "x")`, ensure `obj` has the right type
3. **Explicit > implicit**: If a default is never used, remove it or document why it exists
4. **Clean code**: ASCII art and emojis are visual noise in production code

## License

MIT
