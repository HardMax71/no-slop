"""
no-slop: Detect AI-generated code patterns.

A collection of linting tools to detect common AI-slop patterns:
- Redundant runtime type checks when static types suffice
- Runtime checks on untyped/Any values (should add types instead)
- Stylistic patterns like ASCII art, emojis, excessive docstrings
- Unused default parameter values

Components:
- mypy plugin: Type-based checks (isinstance, hasattr, getattr, callable)
- flake8 plugin: Style checks (ASCII art, emojis, excessive docstrings)
- CLI tool: Unused defaults analysis (whole-program call graph)

Installation:
    pip install no-slop

    # mypy.ini or pyproject.toml
    [tool.mypy]
    plugins = ["no_slop.mypy_plugin"]

    # flake8 auto-registers via entry points
"""

__version__ = "0.1.0"

from no_slop.flake8_plugin import SlopStyleChecker
from no_slop.mypy_plugin import NoSlopPlugin
from no_slop.unused_defaults import UnusedDefaultsChecker

__all__ = ["NoSlopPlugin", "SlopStyleChecker", "UnusedDefaultsChecker", "__version__"]
