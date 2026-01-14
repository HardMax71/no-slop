from __future__ import annotations

from no_slop.rules.flake8.ascii_art import check_ascii_art
from no_slop.rules.flake8.base import (
    MAX_DOCSTRING_CODE_RATIO,
    MAX_MODULE_DOCSTRING_LINES,
    IgnoreHandler,
)
from no_slop.rules.flake8.docstrings import (
    check_leading_comments,
    check_module_docstring,
)
from no_slop.rules.flake8.emojis import check_emojis

__all__ = [
    "MAX_DOCSTRING_CODE_RATIO",
    "MAX_MODULE_DOCSTRING_LINES",
    "IgnoreHandler",
    "check_ascii_art",
    "check_emojis",
    "check_leading_comments",
    "check_module_docstring",
]
