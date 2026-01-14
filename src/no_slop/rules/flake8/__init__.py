from __future__ import annotations

from no_slop.rules.flake8.ascii_art import check_ascii_art
from no_slop.rules.flake8.base import (
    MAX_DOCSTRING_CODE_RATIO,
    MAX_DOCSTRING_LINES_ABSOLUTE,
    MAX_LEADING_COMMENT_LINES,
    MAX_MODULE_DOCSTRING_LINES,
    IgnoreHandler,
)
from no_slop.rules.flake8.docstrings import (
    check_leading_comments,
    check_module_docstring,
)
from no_slop.rules.flake8.emojis import check_emojis
from no_slop.rules.flake8.indirect_access import check_indirect_access
from no_slop.rules.flake8.local_imports import check_local_imports
from no_slop.rules.flake8.redundant_patterns import check_redundant_patterns

__all__ = [
    "MAX_DOCSTRING_CODE_RATIO",
    "MAX_DOCSTRING_LINES_ABSOLUTE",
    "MAX_LEADING_COMMENT_LINES",
    "MAX_MODULE_DOCSTRING_LINES",
    "IgnoreHandler",
    "check_ascii_art",
    "check_emojis",
    "check_indirect_access",
    "check_leading_comments",
    "check_local_imports",
    "check_module_docstring",
    "check_redundant_patterns",
]
