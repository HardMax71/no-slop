from __future__ import annotations

import re
from collections.abc import Iterator

from no_slop.rules.flake8.base import IgnoreHandler

# Detection patterns for ASCII art
ASCII_ART_PATTERNS = [
    re.compile(r"[│┃┆┇┊┋|]{3,}"),
    re.compile(r"[─━┄┅┈┉]{5,}"),
    re.compile(r"[╔╗╚╝╠╣╦╩╬═║]+"),
    re.compile(r"[┌┐└┘├┤┬┴┼─│]+"),
    re.compile(r"[▀▁▂▃▄▅▆▇█▉▊▋▌▍▎▏]+"),
    re.compile(r"[░▒▓]+"),
    re.compile(r"[★☆✦✧◆◇○●]+"),
    re.compile(r"(<{5,}|>{5,})"),
    re.compile(r"(\^{5,}|v{5,})"),
]

# Allowed separator patterns (simple comment dividers)
SIMPLE_SEPARATOR = re.compile(r"^[-=*~#]{3,}$")
SECTION_HEADER_START = re.compile(r"^[A-Z][A-Z0-9 _:]+[-=*~#]{3,}$")
SECTION_HEADER_WRAPPED = re.compile(r"^[-=*~#]{3,}\s+[A-Z][A-Za-z0-9 _:]+\s*[-=*~#]*$")

# Classification patterns for error messages
BOX_DRAWING_CHARS = re.compile(r"[╔╗╚╝╠╣╦╩╬║│┃┌┐└┘├┤┬┴┼]")
BLOCK_DRAWING_CHARS = re.compile(r"[▀▁▂▃▄▅▆▇█▉▊▋▌▍▎▏░▒▓]{3,}")
ARROW_PATTERN = re.compile(r"[<>]{10,}|[\^v]{10,}")


def check_ascii_art(
    lines: list[str],
    ignores: IgnoreHandler,
    checker_type: type,
) -> Iterator[tuple[int, int, str, type]]:
    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if stripped.startswith("#"):
            after_hash = stripped[1:].strip()
            if SIMPLE_SEPARATOR.match(after_hash):
                continue
            if SECTION_HEADER_START.match(after_hash):
                continue
            if SECTION_HEADER_WRAPPED.match(after_hash):
                continue

        for pattern in ASCII_ART_PATTERNS:
            if pattern.search(line):
                if ignores.should_ignore(i, "SLP021"):
                    break

                if BOX_DRAWING_CHARS.search(line):
                    yield (
                        i,
                        0,
                        "SLP021 Box-drawing ASCII art detected. Keep code clean.",
                        checker_type,
                    )
                    break

                if BLOCK_DRAWING_CHARS.search(line):
                    yield (
                        i,
                        0,
                        "SLP021 Block-drawing ASCII art detected. Keep code clean.",
                        checker_type,
                    )
                    break

                if ARROW_PATTERN.search(line):
                    yield (
                        i,
                        0,
                        "SLP021 Decorative arrow pattern detected. Keep code clean.",
                        checker_type,
                    )
                    break
