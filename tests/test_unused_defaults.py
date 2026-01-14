"""Unit tests for the unused defaults checker."""

from __future__ import annotations

import tempfile
from pathlib import Path

from no_slop.unused_defaults import UnusedDefaultsChecker


def check_project(files: dict[str, str]) -> list[dict]:
    """Create a temp project and run the checker."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        for name, content in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

        checker = UnusedDefaultsChecker(str(root), quiet=True)
        issues = checker.analyze()

        return [
            {
                "function": i.function_name,
                "param": i.param_name,
                "default": i.default_value,
                "call_sites": i.num_call_sites,
            }
            for i in issues
        ]


class TestUnusedDefaults:
    """Tests for detecting unused default parameter values."""

    def test_default_never_used(self) -> None:
        files = {
            "main.py": """
def process(x: int, y: int = 10) -> int:
    return x + y

# All calls provide explicit y
a = process(1, 2)
b = process(3, 4)
c = process(5, 6)
"""
        }
        issues = check_project(files)
        assert len(issues) == 1
        assert issues[0]["function"] == "process"
        assert issues[0]["param"] == "y"
        assert issues[0]["default"] == "10"
        assert issues[0]["call_sites"] == 3

    def test_default_sometimes_used(self) -> None:
        files = {
            "main.py": """
def process(x: int, y: int = 10) -> int:
    return x + y

# Mixed calls - some use default
a = process(1)       # Uses default
b = process(3, 4)    # Explicit
c = process(5)       # Uses default
"""
        }
        issues = check_project(files)
        # Should NOT flag - default is used
        assert len(issues) == 0

    def test_keyword_argument(self) -> None:
        files = {
            "main.py": """
def format_msg(text: str, prefix: str = "[INFO]") -> str:
    return f"{prefix} {text}"

# All calls provide explicit prefix as keyword
a = format_msg("hello", prefix="[WARN]")
b = format_msg("world", prefix="[ERROR]")
"""
        }
        issues = check_project(files)
        assert len(issues) == 1
        assert issues[0]["param"] == "prefix"

    def test_kwonly_param_never_used(self) -> None:
        files = {
            "main.py": """
def fetch(url: str, *, timeout: int = 30) -> str:
    return url

# All calls provide explicit timeout
a = fetch("http://a.com", timeout=10)
b = fetch("http://b.com", timeout=20)
"""
        }
        issues = check_project(files)
        assert len(issues) == 1
        assert issues[0]["param"] == "timeout"

    def test_kwonly_param_sometimes_used(self) -> None:
        files = {
            "main.py": """
def fetch(url: str, *, timeout: int = 30) -> str:
    return url

# Mixed - some use default
a = fetch("http://a.com")  # Uses default
b = fetch("http://b.com", timeout=20)
"""
        }
        issues = check_project(files)
        assert len(issues) == 0

    def test_star_args_prevents_detection(self) -> None:
        files = {
            "main.py": """
def process(x: int, y: int = 10) -> int:
    return x + y

args = (1, 2)
a = process(*args)  # Can't know if y is provided
"""
        }
        issues = check_project(files)
        # Can't be sure due to *args, should not flag
        assert len(issues) == 0

    def test_double_star_kwargs_prevents_detection(self) -> None:
        files = {
            "main.py": """
def process(x: int, y: int = 10) -> int:
    return x + y

kwargs = {"x": 1, "y": 2}
a = process(**kwargs)  # Can't know if y is provided
"""
        }
        issues = check_project(files)
        # Can't be sure due to **kwargs, should not flag
        assert len(issues) == 0

    def test_multiple_files(self) -> None:
        files = {
            "lib.py": """
def helper(data: str, debug: bool = False) -> str:
    return data
""",
            "main.py": """
from lib import helper

a = helper("a", debug=True)
b = helper("b", debug=False)
""",
        }
        issues = check_project(files)
        assert len(issues) == 1
        assert issues[0]["function"] == "helper"
        assert issues[0]["param"] == "debug"

    def test_method_calls(self) -> None:
        files = {
            "main.py": """
class Service:
    def process(self, x: int, y: int = 10) -> int:
        return x + y

s = Service()
a = s.process(1, 2)
b = s.process(3, 4)
"""
        }
        issues = check_project(files)
        assert len(issues) == 1
        assert issues[0]["function"] == "process"
        assert issues[0]["param"] == "y"

    def test_none_default(self) -> None:
        files = {
            "main.py": """
from typing import Optional

def get_config(path: str, fallback: Optional[str] = None) -> str:
    return fallback or path

# All calls provide explicit fallback
a = get_config("/a", "/b")
b = get_config("/c", "/d")
"""
        }
        issues = check_project(files)
        assert len(issues) == 1
        assert issues[0]["default"] == "None"

    def test_no_call_sites_no_issue(self) -> None:
        files = {
            "lib.py": """
def unused_func(x: int, y: int = 10) -> int:
    return x + y
# No calls to unused_func
"""
        }
        issues = check_project(files)
        # No call sites means we can't determine if default is used
        assert len(issues) == 0

    def test_private_functions_skipped(self) -> None:
        files = {
            "main.py": """
def _private(x: int, y: int = 10) -> int:
    return x + y

# All calls provide explicit y
a = _private(1, 2)
b = _private(3, 4)
"""
        }
        issues = check_project(files)
        # Private functions are skipped by default
        assert len(issues) == 0

    def test_class_constructor_calls(self) -> None:
        # Note: Foo(1, 2) matches by class name, not __init__
        # This is expected behavior - constructor calls go through the class
        files = {
            "main.py": """
class Foo:
    def __init__(self, x: int, y: int = 10) -> None:
        self.x = x
        self.y = y

# Mixed calls - some use default
a = Foo(1, 2)
b = Foo(3)  # Uses default
"""
        }
        issues = check_project(files)
        # Default is used, should not flag
        assert len(issues) == 0
