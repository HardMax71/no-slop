from __future__ import annotations

import re
from collections.abc import Iterator

from no_slop.rules.flake8.base import IgnoreHandler

EMOJI_PATTERN = re.compile(
    "["
    "\U0001f600-\U0001f64f"
    "\U0001f300-\U0001f5ff"
    "\U0001f680-\U0001f6ff"
    "\U0001f1e0-\U0001f1ff"
    "\U00002702-\U000027b0"
    "\U0001f900-\U0001f9ff"
    "\U0001fa00-\U0001fa6f"
    "\U0001fa70-\U0001faff"
    "\U00002600-\U000026ff"
    "\U0001f700-\U0001f77f"
    "]+",
    flags=re.UNICODE,
)


def check_emojis(
    lines: list[str],
    ignores: IgnoreHandler,
    checker_type: type,
) -> Iterator[tuple[int, int, str, type]]:
    for i, line in enumerate(lines, 1):
        matches = EMOJI_PATTERN.findall(line)
        if matches:
            if ignores.should_ignore(i, "SLP022"):
                continue

            first_match = EMOJI_PATTERN.search(line)
            col = first_match.start() if first_match else 0

            yield (
                i,
                col,
                f"SLP022 Emoji detected: {' '.join(matches)}. Keep code professional.",
                checker_type,
            )
