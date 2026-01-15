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

| Code              | Description                                            |
|-------------------|--------------------------------------------------------|
| `slop-isinstance` | `isinstance(x, T)` when `x: T` is guaranteed           |
| `slop-issubclass` | `issubclass(C, T)` when `C` is subclass of `T`         |
| `slop-hasattr`    | `hasattr(obj, "attr")` when type guarantees attr       |
| `slop-getattr`    | `getattr(obj, "attr")` when attr guaranteed            |
| `slop-setattr`    | `setattr(obj, "attr", val)` when attr guaranteed       |
| `slop-delattr`    | `delattr(obj, "attr")` when attr guaranteed            |
| `slop-callable`   | `callable(f)` when `f` is typed as `Callable`          |
| `slop-dict-get`   | `TypedDict.get("key", default)` when key is required   |
| `slop-any-check`  | Reflection on `Any`/`object`/untyped values            |

### flake8 Plugin

| Code     | Description                                      |
|----------|--------------------------------------------------|
| `SLP020` | Excessive module docstring or leading comments   |
| `SLP021` | ASCII art (box drawing, block characters)        |
| `SLP022` | Emojis in code                                   |
| `SLP023` | Local imports (imports inside functions)         |
| `SLP030` | Conversational residue (e.g., "Here is the code")|
| `SLP031` | Obvious comments (e.g., "# Import modules")      |
| `SLP032` | Generic variable names in function signature     |
| `SLP401` | `obj.__dict__.get()` instead of direct access    |
| `SLP402` | `obj.__dict__[key]` instead of `obj.attr`        |
| `SLP403` | `obj.__dict__[key] = val` instead of `obj.attr=` |
| `SLP404` | `obj.__dict__.update()` instead of assignment    |
| `SLP405` | `vars(obj).get()` instead of direct access       |
| `SLP406` | `vars(obj)[key] = val` instead of assignment     |
| `SLP407` | `asdict(obj).get()` instead of `obj.attr`        |
| `SLP408` | `.get("key", default)` when key is in dict       |
| `SLP501` | Unnecessary else after return/raise/break/continue |
| `SLP502` | Redundant boolean comparison (== True/False/None, len(x) == 0) |
| `SLP503` | Unnecessary pass in non-empty block              |
| `SLP504` | Bare except or `except Exception: pass`          |
| `SLP505` | Mutable default argument (def f(x=[]))           |
| `SLP506` | f-string with no placeholders                    |
| `SLP507` | Redundant list()/dict() wrapping                 |
| `SLP508` | Unnecessary .keys() in iteration                 |
| `SLP509` | Explicit `return None` at end of function        |
| `SLP510` | `type(x) == T` instead of `isinstance(x, T)`     |
| `SLP601` | Redundant loop guarding (`if x: for y in x:`)    |
| `SLP602` | Unpythonic loop (`for i in range(len(x))` with indexing) |

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

### getattr (slop-getattr)

```python
def get_email(user: User) -> str:
    return getattr(user, "email", "none")  # Redundant - User always has 'email'
    # Also flags: getattr(user, "email") without default
```

### setattr (slop-setattr)

```python
def set_name(user: User, name: str) -> None:
    setattr(user, "name", name)  # Redundant - use user.name = name
```

### delattr (slop-delattr)

```python
def clear_name(user: User) -> None:
    delattr(user, "name")  # Redundant - use del user.name
```

### callable (SLOP005)

```python
def invoke(func: Callable[[], int]) -> int:
    if callable(func):  # Redundant - func is Callable
        return func()
    return 0
```

### dict-get (slop-dict-get)

```python
from typing import TypedDict

class Config(TypedDict):
    host: str  # Required key

def get_host(config: Config) -> str:
    return config.get("host", "default")  # Redundant - host always exists
    # Use: config["host"]
```

### any-check (slop-any-check)

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

### Conversational Residue (SLP030)

```python
# Here is the updated code
def process():
    # As an AI model I suggest
    pass
```

Remove these chat artifacts.

### Obvious Comments (SLP031)

```python
# Import modules
import os

# Define function
def calculate():
    pass
```

Comments should explain *why*, not *what*.

### Generic Variable Names (SLP032)

```python
def process_data(data, val):  # Bad
    pass

def process_user(user_profile, score):  # Good
    pass
```

Avoid `data`, `res`, `val`, `item`, `obj`, `content`, `info`, `result` in function signatures.

### Indirect access patterns (SLP401-SLP407)

```python
from dataclasses import dataclass, asdict

@dataclass
class User:
    name: str

user = User("John")

# SLP401: __dict__.get()
user.__dict__.get("name", "")  # Bad - use user.name or getattr()

# SLP402: __dict__[key] read
user.__dict__["name"]  # Bad - use user.name

# SLP403: __dict__[key] write
user.__dict__["name"] = "Jane"  # Bad - use user.name = "Jane"

# SLP404: __dict__.update()
user.__dict__.update({"name": "Jane"})  # Bad - use user.name = "Jane"

# SLP405: vars().get()
vars(user).get("name", "")  # Bad - use user.name or getattr()

# SLP406: vars()[key] write
vars(user)["name"] = "Jane"  # Bad - use user.name = "Jane"

# SLP407: asdict().get()
asdict(user).get("name", "")  # Bad - use user.name directly
```

These patterns bypass direct attribute access and are almost always unnecessary.

### Dict .get() on known keys (SLP408)

```python
# Inline - key is in the literal
x = {"host": "localhost"}.get("host", "default")  # Bad
x = dict(host="localhost").get("host", "default")  # Bad

# Variable - key was just defined
config = {"host": "localhost", "port": 8080}
host = config.get("host", "default")  # Bad - use config["host"]

# OK - no default
host = config.get("host")

# OK - key not in original dict
timeout = config.get("timeout", 30)

# OK - key might have been removed
config.pop("host")
host = config.get("host", "default")
```

When you define a dict with known keys, using `.get("key", default)` on those keys is redundant - the key is guaranteed to exist.

### Unnecessary else (SLP501)

```python
def process(x: int) -> str:
    if x < 0:
        return "negative"
    else:
        # This else is unnecessary - can be dedented
        log("processing positive")
        return "positive"
```

Fix: Remove the else and dedent the code.

```python
def process(x: int) -> str:
    if x < 0:
        return "negative"
    log("processing positive")
    return "positive"
```

Note: Single-statement else blocks (e.g., `if x: return 1 else: return 0`) are NOT flagged as they're a valid, clear pattern.

### Redundant boolean comparisons (SLP502)

```python
# Bad
if enabled == True:      # Use: if enabled
if enabled == False:     # Use: if not enabled
if value == None:        # Use: if value is None
if value != None:        # Use: if value is not None
if len(items) == 0:      # Use: if not items
if len(items) > 0:       # Use: if items
```

### Unnecessary pass (SLP503)

```python
# Bad - pass is unnecessary when block has other statements
def foo():
    x = 1
    pass  # Remove this

# OK - pass is the only statement
class Empty:
    pass
```

### Bare except / exception swallowing (SLP504)

```python
# Bad - catches all exceptions including KeyboardInterrupt
try:
    risky()
except:
    pass

# Bad - swallows all exceptions silently
try:
    risky()
except Exception:
    pass

# OK - handles specific exception
try:
    risky()
except ValueError:
    log("value error")

# OK - at least logs the exception
try:
    risky()
except Exception:
    log_error()
```

### Mutable default arguments (SLP505)

```python
# Bad - list is created once and shared between calls
def append_item(items=[]):
    items.append(1)
    return items

# Bad - same issue with dict
def update_config(config={}):
    config["key"] = "value"
    return config

# Good - use None and initialize in body
def append_item(items=None):
    if items is None:
        items = []
    items.append(1)
    return items
```

### f-string without placeholders (SLP506)

```python
# Bad - no reason to use f-string
message = f"Hello World"

# Good - use regular string
message = "Hello World"

# Good - f-string with actual placeholders
name = "World"
message = f"Hello {name}"
```

### Redundant wrapping (SLP507)

```python
# Bad - use [] instead
items = list()

# Bad - list literal inside list()
items = list([1, 2, 3])

# Bad - use {} instead
config = dict()

# Bad - dict literal inside dict()
config = dict({"a": 1})

# OK - converting iterator to list
items = list(range(10))

# OK - dict with keyword args
config = dict(a=1, b=2)
```

### Unnecessary .keys() (SLP508)

```python
# Bad - .keys() is redundant in iteration
for key in data.keys():
    print(key)

# Good - iterate directly
for key in data:
    print(key)

# OK - .keys() is needed for set operations
common = data.keys() & other.keys()
```

### Explicit return None (SLP509)

```python
# Bad - explicit return None at end is redundant
def process(x):
    print(x)
    return None

# Bad - bare return at end is also redundant
def process(x):
    print(x)
    return

# Good - just omit the return
def process(x):
    print(x)

# OK - return None in middle for early exit
def process(x):
    if x < 0:
        return None
    return x * 2
```

### type() comparison (SLP510)

```python
# Bad - doesn't handle subclasses
if type(x) == int:
    process(x)

# Good - handles subclasses correctly
if isinstance(x, int):
    process(x)
```

### Redundant loop guarding (SLP601)

```python
# Bad - if check is redundant because loop won't run if empty
if items:
    for item in items:
        process(item)

# Good
for item in items:
    process(item)
```

### Unpythonic loop (SLP602)

```python
# Bad - C-style iteration
for i in range(len(items)):
    print(items[i])

# Good - direct iteration
for item in items:
    print(item)

# Good - if index is needed
for i, item in enumerate(items):
    print(i, item)
```

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
