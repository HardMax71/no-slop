from __future__ import annotations

import re

SLP033 = "SLP033 Placeholder body. Implement or remove stub."
SLP034 = "SLP034 Orphaned placeholder comment found. Add context or resolve."
SLP035 = "SLP035 Debug artifact left in code. Remove or guard."
SLP036 = "SLP036 Cross-language API '{attr}' on Python literal or annotated type."
SLP037 = "SLP037 Unresolvable import '{module}'. Verify module exists."
SLP038 = "SLP038 Hedging comment found. Make behavior explicit."
SLP039 = "SLP039 Single-method class wrapper. Consider a function or dataclass."
SLP040 = "SLP040 Function too complex ({detail})."

TODO_PATTERN = re.compile(r"\b(TODO|FIXME|XXX|TBD)\b", re.IGNORECASE)
TRACKING_PATTERN = re.compile(
    r"(@\w+|#\d+|\b[A-Z]{2,}-\d+\b|\b(owner|assignee|assigned|ticket|issue|jira)\b|"
    r"\b20\d{2}-\d{2}-\d{2}\b|https?://\S+|todo\([^)]*\))",
    re.IGNORECASE,
)
GENERIC_TODO_PATTERN = re.compile(
    r"\b(implement( later| this)?|add (error handling|logging|validation|tests?)|"
    r"handle (errors?|edge cases?)|(edge|corner) cases?|optimi[sz]e|cleanup|refactor|"
    r"placeholder|stub|fill in|wire up)\b",
    re.IGNORECASE,
)
HEDGE_PATTERN = re.compile(
    r"\b(maybe|probably|hopefully|not\s+sure|i\s+think|seems?|should\s+work)\b",
    re.IGNORECASE,
)

UNION_TYPE_NAMES = {"Optional", "Union"}
TYPE_ALIASES = {
    "list": "list",
    "List": "list",
    "dict": "dict",
    "Dict": "dict",
    "set": "set",
    "Set": "set",
    "AbstractSet": "AbstractSet",
    "MutableSet": "MutableSet",
    "Sequence": "Sequence",
    "MutableSequence": "MutableSequence",
    "Mapping": "Mapping",
    "MutableMapping": "MutableMapping",
    "str": "str",
    "Text": "str",
}
TYPE_METHOD_SOURCES = {
    "builtins.pyi": {"list", "dict", "set", "str"},
    "typing.pyi": {
        "Sequence",
        "MutableSequence",
        "Mapping",
        "MutableMapping",
        "AbstractSet",
        "MutableSet",
    },
}

CROSS_LANGUAGE_ATTRS = {
    "push",
    "shift",
    "unshift",
    "length",
    "equals",
    "charAt",
    "substring",
    "substr",
    "indexOf",
    "toUpperCase",
    "toLowerCase",
    "includes",
}

DEBUG_CALLS = {"print", "breakpoint"}
DEBUG_ATTR_CALLS = {
    ("pdb", "set_trace"),
    ("ipdb", "set_trace"),
    ("icecream", "ic"),
}

MAX_NESTING_DEPTH = 4
MAX_FUNCTION_LINES = 80
