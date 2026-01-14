<div align="center">

# no-slop

**Detect AI-generated code patterns via static analysis**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![mypy](https://img.shields.io/badge/mypy-plugin-blue.svg)](https://mypy.readthedocs.io/)
[![flake8](https://img.shields.io/badge/flake8-plugin-blue.svg)](https://flake8.pycqa.org/)
[![CI](https://github.com/HardMax71/no-slop/actions/workflows/ci.yml/badge.svg)](https://github.com/HardMax71/no-slop/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/HardMax71/no-slop/branch/master/graph/badge.svg)](https://codecov.io/gh/HardMax71/no-slop)
[![PyPI](https://img.shields.io/pypi/v/no-slop.svg)](https://pypi.org/project/no-slop/)

</div>

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
