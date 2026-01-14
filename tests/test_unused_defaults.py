from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from no_slop.unused_defaults import UnusedDefaultsChecker, main


def check_project(files: dict[str, str]) -> list[dict]:
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


class TestUnusedDefaultsMain:
    """Tests for the main() function directly (for coverage)."""

    def test_main_with_issues(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            code = """
def process(x: int, y: int = 10) -> int:
    return x + y

a = process(1, 2)
"""
            path = Path(tmpdir) / "test.py"
            path.write_text(code)

            with patch("sys.argv", ["unused_defaults", tmpdir]):
                result = main()
            assert result == 1

    def test_main_no_issues(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            code = """
def process(x: int, y: int = 10) -> int:
    return x + y

a = process(1)
"""
            path = Path(tmpdir) / "test.py"
            path.write_text(code)

            with patch("sys.argv", ["unused_defaults", tmpdir]):
                result = main()
            assert result == 0

    def test_main_json_output(self, capsys: object) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            code = """
def process(x: int, y: int = 10) -> int:
    return x + y

a = process(1, 2)
"""
            path = Path(tmpdir) / "test.py"
            path.write_text(code)

            with patch("sys.argv", ["unused_defaults", "--json", tmpdir]):
                main()
            captured = capsys.readouterr()  # type: ignore[attr-defined]
            output = json.loads(captured.out)
            assert len(output) == 1
            assert output[0]["code"] == "SLOP010"

    def test_main_min_calls_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            code = """
def process(x: int, y: int = 10) -> int:
    return x + y

a = process(1, 2)
"""
            path = Path(tmpdir) / "test.py"
            path.write_text(code)

            with patch("sys.argv", ["unused_defaults", "--min-calls", "5", tmpdir]):
                result = main()
            assert result == 0


class TestUnusedDefaultsCLI:
    """Tests for the CLI interface."""

    def test_cli_basic(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            code = """
def process(x: int, y: int = 10) -> int:
    return x + y

a = process(1, 2)
b = process(3, 4)
"""
            path = Path(tmpdir) / "test.py"
            path.write_text(code)

            result = subprocess.run(
                [sys.executable, "-m", "no_slop.unused_defaults", tmpdir],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 1
            assert "SLOP010" in result.stdout
            assert "process" in result.stdout
            assert "y = 10" in result.stdout

    def test_cli_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            code = """
def process(x: int, y: int = 10) -> int:
    return x + y

a = process(1, 2)
"""
            path = Path(tmpdir) / "test.py"
            path.write_text(code)

            result = subprocess.run(
                [sys.executable, "-m", "no_slop.unused_defaults", "--json", tmpdir],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 1
            output = json.loads(result.stdout)
            assert len(output) == 1
            assert output[0]["code"] == "SLOP010"
            assert output[0]["function"] == "process"
            assert output[0]["param"] == "y"

    def test_cli_no_issues(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            code = """
def process(x: int, y: int = 10) -> int:
    return x + y

a = process(1)  # Uses default
"""
            path = Path(tmpdir) / "test.py"
            path.write_text(code)

            result = subprocess.run(
                [sys.executable, "-m", "no_slop.unused_defaults", tmpdir],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0
            assert "Found 0 unused defaults" in result.stdout

    def test_cli_min_calls(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            code = """
def process(x: int, y: int = 10) -> int:
    return x + y

a = process(1, 2)  # Only 1 call
"""
            path = Path(tmpdir) / "test.py"
            path.write_text(code)

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "no_slop.unused_defaults",
                    "--min-calls",
                    "2",
                    tmpdir,
                ],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0

    def test_cli_quiet(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            code = """
def process(x: int, y: int = 10) -> int:
    return x + y

a = process(1, 2)
"""
            path = Path(tmpdir) / "test.py"
            path.write_text(code)

            result = subprocess.run(
                [sys.executable, "-m", "no_slop.unused_defaults", "-q", tmpdir],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 1
            assert "Analyzing" not in result.stderr


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
        assert len(issues) == 0

    def test_async_function(self) -> None:
        files = {
            "main.py": """
async def fetch(url: str, timeout: int = 30) -> str:
    return url

import asyncio
asyncio.run(fetch("http://test.com", timeout=10))
"""
        }
        issues = check_project(files)
        assert len(issues) == 1
        assert issues[0]["function"] == "fetch"
        assert issues[0]["param"] == "timeout"

    def test_kwonly_without_default(self) -> None:
        files = {
            "main.py": """
def process(x: int, *, required: str, optional: int = 10) -> int:
    return x

# All calls
a = process(1, required="a", optional=5)
"""
        }
        issues = check_project(files)
        assert len(issues) == 1
        assert issues[0]["param"] == "optional"

    def test_various_default_types(self) -> None:
        files = {
            "main.py": """
def func(
    a: list = [],
    b: dict = {},
    c: set = {1},
    d: tuple = (),
    e: object = dict(),
    f: callable = lambda: 1,
    g: int = -1,
) -> None:
    pass

func([], {}, {2}, (), dict(), lambda: 2, -2)
func([], {}, {3}, (), dict(), lambda: 3, -3)
"""
        }
        issues = check_project(files)
        assert len(issues) == 7
        defaults = {i["param"]: i["default"] for i in issues}
        assert defaults["a"] == "[...]"
        assert defaults["b"] == "{...}"
        assert defaults["c"] == "{...}"
        assert defaults["d"] == "(...)"
        assert defaults["e"] == "dict()"
        assert defaults["f"] == "lambda"
        assert defaults["g"] == "-1"

    def test_default_is_variable_name(self) -> None:
        files = {
            "main.py": """
DEFAULT_VALUE = 42

def func(x: int = DEFAULT_VALUE) -> int:
    return x

func(10)
func(20)
"""
        }
        issues = check_project(files)
        assert len(issues) == 1
        assert issues[0]["default"] == "DEFAULT_VALUE"

    def test_default_is_method_call(self) -> None:
        files = {
            "main.py": """
class Factory:
    @staticmethod
    def create():
        return 1

def func(x: int = Factory.create()) -> int:
    return x

func(10)
"""
        }
        issues = check_project(files)
        assert len(issues) == 1
        assert issues[0]["default"] == "<call>"

    def test_default_is_complex_expression(self) -> None:
        files = {
            "main.py": """
def func(x: int = 1 + 2) -> int:
    return x

func(10)
"""
        }
        issues = check_project(files)
        assert len(issues) == 1
        assert issues[0]["default"] == "<expr>"

    def test_syntax_error_file_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "good.py").write_text("""
def func(x: int = 10) -> int:
    return x

func(20)
""")
            (root / "bad.py").write_text("def broken syntax")

            checker = UnusedDefaultsChecker(str(root), quiet=True)
            issues = checker.analyze()
            assert len(issues) == 1
            assert issues[0].function_name == "func"

    def test_call_expression_callee(self) -> None:
        files = {
            "main.py": """
def factory():
    def inner(x: int = 10):
        return x
    return inner

# Calling result of factory() - can't resolve callee
factory()(5)
"""
        }
        issues = check_project(files)
        assert len(issues) == 0

    def test_hidden_directory_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "good.py").write_text("""
def func(x: int = 10) -> int:
    return x

func(20)
""")
            hidden = root / ".hidden"
            hidden.mkdir()
            (hidden / "bad.py").write_text("""
def other(y: int = 20) -> int:
    return y

other(30)
""")

            checker = UnusedDefaultsChecker(str(root), quiet=True)
            issues = checker.analyze()
            assert len(issues) == 1
            assert issues[0].function_name == "func"
