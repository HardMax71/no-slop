# no-slop Documentation

## Error Codes

### mypy Plugin (Type-based checks)

| Code              | Description                                                      |
|-------------------|------------------------------------------------------------------|
| `slop-isinstance` | `isinstance(x, T)` when `x: T` is already guaranteed             |
| `slop-issubclass` | `issubclass(C, T)` when `C` is already a subclass of `T`         |
| `slop-hasattr`    | `hasattr(obj, "attr")` when type guarantees attr exists          |
| `slop-getattr`    | `getattr(obj, "attr", default)` when type guarantees attr exists |
| `slop-callable`   | `callable(f)` when `f` is typed as `Callable`                    |
| `slop-any-check`  | Any reflection on `Any`/`object`/untyped values                  |

### flake8 Plugin (Style checks)

| Code      | Description                                         |
|-----------|-----------------------------------------------------|
| `SLOP020` | Excessive module docstring or leading comment block |
| `SLOP021` | ASCII art (box drawing, block characters)           |
| `SLOP022` | Emojis in code                                      |

### Unused Defaults CLI

| Code      | Description                                              |
|-----------|----------------------------------------------------------|
| `SLOP010` | Default parameter value never used across all call sites |

## Examples

### Redundant isinstance (SLOP001)

```python
from dataclasses import dataclass

@dataclass
class User:
    name: str

def process(user: User) -> str:
    # SLOP001: Redundant isinstance - user is always User
    if isinstance(user, User):
        return user.name
    return ""
```

### Redundant hasattr (SLOP003)

```python
def get_name(user: User) -> str:
    # SLOP003: Redundant hasattr - User always has 'name'
    if hasattr(user, "name"):
        return user.name
    return ""
```

### Redundant getattr (SLOP004)

```python
def get_email(user: User) -> str:
    # SLOP004: Redundant getattr - User always has 'email'
    return getattr(user, "email", "none")
```

### Redundant callable (SLOP005)

```python
from typing import Callable

def invoke(func: Callable[[], int]) -> int:
    # SLOP005: Redundant callable - func is Callable
    if callable(func):
        return func()
    return 0
```

### Runtime check on untyped (SLOP007)

```python
def bad_pattern(data):  # No type annotation!
    # SLOP007: isinstance on untyped value - add annotation instead
    if isinstance(data, dict):
        return data.get("key")
```

### Unused default (SLOP010)

```python
# lib.py
def process(data: list[int], multiplier: int = 1) -> list[int]:
    return [x * multiplier for x in data]

# main.py - ALL calls provide explicit multiplier
result1 = process([1, 2, 3], 2)
result2 = process([4, 5], 3)
# The default value `1` is dead code!
```

## Ignoring Errors

### mypy plugin

```python
if hasattr(user, "name"):  # type: ignore[slop-hasattr]
    ...
```

### flake8 plugin

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

## Configuration

### pyproject.toml

```toml
[tool.mypy]
plugins = ["no_slop.mypy_plugin"]
```

### mypy.ini

```ini
[mypy]
plugins = no_slop.mypy_plugin
```

## CLI Options

### no-slop-unused-defaults

```bash
no-slop-unused-defaults /path/to/project
no-slop-unused-defaults . --json
no-slop-unused-defaults . --min-calls 3
no-slop-unused-defaults . --quiet
```

| Option          | Description                               |
|-----------------|-------------------------------------------|
| `--json`        | Output as JSON                            |
| `--min-calls N` | Only report if N+ call sites (default: 1) |
| `--quiet`, `-q` | Suppress progress output                  |

## Philosophy

AI-generated code often includes defensive patterns that make sense when types are unknown, but become redundant when
proper type annotations exist:

1. **Trust your types**: If mypy passes, you don't need `isinstance` checks
2. **Type, don't check**: Instead of `if hasattr(obj, "x")`, ensure `obj` has the right type
3. **Explicit > implicit**: If a default is never used, remove it or document why it exists
4. **Clean code**: ASCII art and emojis are visual noise in production code
