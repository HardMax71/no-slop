# no-slop

Detect AI-generated code patterns via static analysis.

## Install

```bash
pip install no-slop
```

## Usage

**mypy plugin** (redundant type checks):
```toml
# pyproject.toml
[tool.mypy]
plugins = ["no_slop.mypy_plugin"]
```

**flake8 plugin** (style checks) - auto-registers on install:
```bash
flake8 your_project/
```

**Unused defaults CLI**:
```bash
no-slop-unused-defaults /path/to/project
```

## What it detects

- Redundant `isinstance`/`hasattr`/`getattr`/`callable` when types guarantee the result
- Runtime checks on `Any`/untyped values (add types instead)
- ASCII art, emojis, excessive docstrings
- Default parameters never used by any call site

See [docs.md](docs.md) for full documentation.

## License

MIT
