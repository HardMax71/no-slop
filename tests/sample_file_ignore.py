# slop: ignore-file[SLOP021, SLOP022]
"""
This file ignores ASCII art and emoji checks at the file level.
Only SLOP020 (excessive docstring) would be checked.
"""

from typing import Optional


# ╔════════════════════════════════════════╗
# ║  This ASCII art is ignored file-wide   ║
# ╚════════════════════════════════════════╝


def process() -> str:
    """Process something. 🚀 ✨ 🎉"""  # Emojis ignored
    return "done"


# ████████████████████████████████████████████
# Block art also ignored
# ████████████████████████████████████████████

x = 42  # 🎯 This emoji is also ignored
