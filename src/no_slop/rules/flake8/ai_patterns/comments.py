from __future__ import annotations

from collections.abc import Iterator

from no_slop.rules.flake8.base import IgnoreHandler

from .constants import (
    GENERIC_TODO_PATTERN,
    HEDGE_PATTERN,
    SLP034,
    SLP038,
    TODO_PATTERN,
    TRACKING_PATTERN,
)


def check_placeholder_comments(
    lines: list[str],
    ignores: IgnoreHandler,
    checker_type: type,
    placeholder_header_lines: set[int],
    placeholder_ranges: list[tuple[int, int]],
) -> Iterator[tuple[int, int, str, type]]:
    for i, line in enumerate(lines, 1):
        comment = _extract_comment(line)
        if not comment:
            continue
        if TODO_PATTERN.search(comment):
            if ignores.should_ignore(i, "SLP034"):
                continue
            if TRACKING_PATTERN.search(comment):
                continue
            generic = GENERIC_TODO_PATTERN.search(comment) is not None
            placeholder_context = _is_placeholder_context(
                i, lines, placeholder_header_lines, placeholder_ranges
            )
            if generic or placeholder_context:
                yield (i, 0, SLP034, checker_type)


def check_hedging_comments(
    lines: list[str],
    ignores: IgnoreHandler,
    checker_type: type,
) -> Iterator[tuple[int, int, str, type]]:
    for i, line in enumerate(lines, 1):
        comment = _extract_comment(line)
        if not comment:
            continue
        if HEDGE_PATTERN.search(comment):
            if not ignores.should_ignore(i, "SLP038"):
                yield (i, 0, SLP038, checker_type)


def _extract_comment(line: str) -> str | None:
    stripped = line.lstrip()
    if not stripped.startswith("#"):
        if "#" not in line:
            return None
        before, after = line.split("#", 1)
        if before.strip().endswith(("'", '"')):
            return None
        return after.strip()
    if stripped.startswith("#!") or stripped.startswith("# -*-"):
        return None
    return stripped[1:].strip()


def _is_placeholder_context(
    line_no: int,
    lines: list[str],
    placeholder_header_lines: set[int],
    placeholder_ranges: list[tuple[int, int]],
) -> bool:
    for start, end in placeholder_ranges:
        if start <= line_no <= end:
            return True
    next_line_no = _next_nonempty_line_no(lines, line_no)
    if next_line_no is not None and next_line_no in placeholder_header_lines:
        return True
    return False


def _next_nonempty_line_no(lines: list[str], line_no: int) -> int | None:
    for idx in range(line_no, len(lines)):
        if lines[idx].strip():
            return idx + 1
    return None
