# no-slop Documentation

## Installation

```bash
pip install no-slop
```

## Components

| Component                 | Purpose                          | Auto-registers    |
|---------------------------|----------------------------------|-------------------|
| `no_slop.mypy_plugin`     | Type-based redundancy checks     | No (needs config) |
| `no_slop.flake8_plugin`   | Style checks (ASCII art, emojis) | Yes               |
| `no-slop-unused-defaults` | Whole-program default analysis   | CLI tool          |

## Error Codes

### mypy Plugin

| Code              | Description                                          |
|-------------------|------------------------------------------------------|
| `slop-isinstance` | `isinstance(x, T)` when `x: T` is guaranteed         |
| `slop-issubclass` | `issubclass(C, T)` when `C` is subclass of `T`       |
| `slop-hasattr`    | `hasattr(obj, "attr")` when type guarantees attr     |
| `slop-getattr`    | `getattr(obj, "attr", default)` when attr guaranteed |
| `slop-callable`   | `callable(f)` when `f` is typed as `Callable`        |
| `slop-any-check`  | Reflection on `Any`/`object`/untyped values          |

### flake8 Plugin

| Code     | Description                                    |
|----------|------------------------------------------------|
| `SLP020` | Excessive module docstring or leading comments |
| `SLP021` | ASCII art (box drawing, block characters)      |
| `SLP022` | Emojis in code                                 |
| `SLP023` | Local imports (imports inside functions)       |

### Unused Defaults CLI

| Code     | Description                                   |
|----------|-----------------------------------------------|
| `SLP010` | Default parameter never used by any call site |

## Configuration

### mypy

```toml
# pyproject.toml
[tool.mypy]
plugins = ["no_slop.mypy_plugin"]
```

```ini
# mypy.ini
[mypy]
plugins = no_slop.mypy_plugin
```

### flake8

Auto-registers on install. No configuration needed.

## Examples

### isinstance (SLOP001)

```python
def process(user: User) -> str:
    if isinstance(user, User):  # Redundant - user is always User
        return user.name
    return ""
```

### issubclass (SLOP002)

```python
def check(cls: type[User]) -> bool:
    return issubclass(cls, User)  # Redundant - cls is always type[User]
```

### hasattr (SLOP003)

```python
def get_name(user: User) -> str:
    if hasattr(user, "name"):  # Redundant - User always has 'name'
        return user.name
    return ""
```

### getattr (SLOP004)

```python
def get_email(user: User) -> str:
    return getattr(user, "email", "none")  # Redundant - User always has 'email'
```

### callable (SLOP005)

```python
def invoke(func: Callable[[], int]) -> int:
    if callable(func):  # Redundant - func is Callable
        return func()
    return 0
```

### any-check (SLOP007)

```python
def bad(data):  # No type annotation
    if isinstance(data, dict):  # Add types instead of runtime checks
        return data.get("key")
```

### Unused default (SLP010)

```python
def process(data: list[int], multiplier: int = 1) -> list[int]:
    return [x * multiplier for x in data]


# All calls provide explicit multiplier - default is dead code
process([1, 2], 2)
process([3, 4], 3)
```

### Local import (SLP023)

```python
def fetch_data(url: str) -> dict:
    import requests  # Bad - move to module level
    return requests.get(url).json()
```

Imports inside functions:
- Hide dependencies
- Run on every call (performance)
- Make code harder to analyze

Exception: `if TYPE_CHECKING:` blocks are allowed.

## Ignoring Errors

### mypy

```python
if hasattr(user, "name"):  # type: ignore[slop-hasattr]
    ...
```

### flake8

```python
x = "hello"  # noqa: SLP022
x = "test"  # noqa: SLP021, SLP022
x = "test"  # noqa

def lazy_import():
    import heavy_module  # noqa: SLP023

# File-level (first 10 lines)
# slop: ignore-file
# slop: ignore-file[SLP021, SLP022]
```

## CLI

```bash
no-slop-unused-defaults /path/to/project
no-slop-unused-defaults . --json
no-slop-unused-defaults . --min-calls 3
no-slop-unused-defaults . --quiet
```

| Option          | Description                           |
|-----------------|---------------------------------------|
| `--json`        | JSON output                           |
| `--min-calls N` | Min call sites to report (default: 1) |
| `--quiet`       | Suppress progress                     |
