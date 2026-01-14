from __future__ import annotations

import re
from collections.abc import Iterator

from no_slop.rules.flake8.base import IgnoreHandler

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


def check_ascii_art(
    lines: list[str],
    ignores: IgnoreHandler,
    checker_type: type,
) -> Iterator[tuple[int, int, str, type]]:
    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if stripped.startswith("#"):
            after_hash = stripped[1:].strip()
            if re.match(r"^[-=*~#]{3,}$", after_hash):
                continue
            if re.match(r"^[A-Z][A-Z0-9 _:]+[-=*~#]{3,}$", after_hash):
                continue
            if re.match(r"^[-=*~#]{3,}\s+[A-Z][A-Za-z0-9 _:]+\s*[-=*~#]*$", after_hash):
                continue

        for pattern in ASCII_ART_PATTERNS:
            if pattern.search(line):
                if ignores.should_ignore(i, "SLOP021"):
                    break

                if re.search(r"[╔╗╚╝╠╣╦╩╬║│┃┌┐└┘├┤┬┴┼]", line):
                    yield (
                        i,
                        0,
                        "SLOP021 Box-drawing ASCII art detected. Keep code clean.",
                        checker_type,
                    )
                    break

                if re.search(r"[▀▁▂▃▄▅▆▇█▉▊▋▌▍▎▏░▒▓]{3,}", line):
                    yield (
                        i,
                        0,
                        "SLOP021 Block-drawing ASCII art detected. Keep code clean.",
                        checker_type,
                    )
                    break

                if re.search(r"[<>]{10,}|[\^v]{10,}", line):
                    yield (
                        i,
                        0,
                        "SLOP021 Decorative arrow pattern detected. Keep code clean.",
                        checker_type,
                    )
                    break
