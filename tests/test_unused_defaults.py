from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import pytest

from no_slop.unused_defaults import UnusedDefaultsChecker, main

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def project(tmp_path: Path) -> Callable[[dict[str, str]], Path]:
    """Create a temporary project with given files."""

    def _create(files: dict[str, str]) -> Path:
        for name, content in files.items():
            path = tmp_path / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        return tmp_path

    return _create


# =============================================================================
# HELPERS
# =============================================================================


def check(root: Path, quiet: bool = True) -> list[dict[str, object]]:
    """Run checker and return simplified results."""
    checker = UnusedDefaultsChecker(str(root), quiet=quiet)
    return [
        {
            "function": i.function_name,
            "param": i.param_name,
            "default": i.default_value,
            "call_sites": i.num_call_sites,
        }
        for i in checker.analyze()
    ]


def run_main(*args: str, cwd: Path) -> int:
    """Run main() with patched argv."""
    with patch("sys.argv", ["unused_defaults", *args, str(cwd)]):
        return main()


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run CLI via subprocess."""
    return subprocess.run(
        [sys.executable, "-m", "no_slop.unused_defaults", *args, str(cwd)],
        capture_output=True,
        text=True,
    )


# =============================================================================
# CODE SNIPPETS - The "what" separated from the "how"
# =============================================================================

CODE_PROCESS = """
def process(x: int, y: int = 10) -> int:
    return x + y
"""

CODE_PROCESS_TWO_CALLS_EXPLICIT = (
    CODE_PROCESS
    + """
a = process(1, 2)
b = process(3, 4)
"""
)

CODE_PROCESS_THREE_CALLS_EXPLICIT = (
    CODE_PROCESS
    + """
a = process(1, 2)
b = process(3, 4)
c = process(5, 6)
"""
)

CODE_PROCESS_MIXED_CALLS = (
    CODE_PROCESS
    + """
a = process(1)       # Uses default
b = process(3, 4)    # Explicit
c = process(5)       # Uses default
"""
)

CODE_PROCESS_ONE_EXPLICIT = (
    CODE_PROCESS
    + """
a = process(1, 2)
"""
)

CODE_PROCESS_ONE_DEFAULT = (
    CODE_PROCESS
    + """
a = process(1)
"""
)


# =============================================================================
# TESTS: Main Function (for coverage)
# =============================================================================


class TestMainFunction:
    """Tests for main() function directly."""

    def test_returns_1_with_issues(
        self, project: Callable[[dict[str, str]], Path]
    ) -> None:
        root = project({"test.py": CODE_PROCESS_ONE_EXPLICIT})
        assert run_main(cwd=root) == 1

    def test_returns_0_no_issues(
        self, project: Callable[[dict[str, str]], Path]
    ) -> None:
        root = project({"test.py": CODE_PROCESS_ONE_DEFAULT})
        assert run_main(cwd=root) == 0

    def test_json_output(
        self,
        project: Callable[[dict[str, str]], Path],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        root = project({"test.py": CODE_PROCESS_ONE_EXPLICIT})
        run_main("--json", cwd=root)

        output = json.loads(capsys.readouterr().out)
        assert len(output) == 1
        assert output[0]["code"] == "SLP010"

    def test_min_calls_filter(self, project: Callable[[dict[str, str]], Path]) -> None:
        root = project({"test.py": CODE_PROCESS_ONE_EXPLICIT})
        # 1 call site but require 5 -> no issues
        assert run_main("--min-calls", "5", cwd=root) == 0


# =============================================================================
# TESTS: CLI Interface
# =============================================================================


class TestCLI:
    """Tests for command-line interface."""

    def test_basic_output(self, project: Callable[[dict[str, str]], Path]) -> None:
        root = project({"test.py": CODE_PROCESS_TWO_CALLS_EXPLICIT})
        result = run_cli(cwd=root)

        assert result.returncode == 1
        assert "SLP010" in result.stdout
        assert "process" in result.stdout
        assert "y = 10" in result.stdout

    def test_json_output(self, project: Callable[[dict[str, str]], Path]) -> None:
        root = project({"test.py": CODE_PROCESS_ONE_EXPLICIT})
        result = run_cli("--json", cwd=root)

        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert len(output) == 1
        assert output[0]["code"] == "SLP010"
        assert output[0]["function"] == "process"
        assert output[0]["param"] == "y"

    def test_no_issues_exit_code(
        self, project: Callable[[dict[str, str]], Path]
    ) -> None:
        root = project({"test.py": CODE_PROCESS_ONE_DEFAULT})
        result = run_cli(cwd=root)

        assert result.returncode == 0
        assert "Found 0 unused defaults" in result.stdout

    def test_min_calls_filter(self, project: Callable[[dict[str, str]], Path]) -> None:
        root = project({"test.py": CODE_PROCESS_ONE_EXPLICIT})
        # 1 call site but require 2 -> no issues
        result = run_cli("--min-calls", "2", cwd=root)
        assert result.returncode == 0

    def test_quiet_mode(self, project: Callable[[dict[str, str]], Path]) -> None:
        root = project({"test.py": CODE_PROCESS_ONE_EXPLICIT})
        result = run_cli("-q", cwd=root)

        assert result.returncode == 1
        assert "Analyzing" not in result.stderr


# =============================================================================
# TESTS: Core Detection Logic
# =============================================================================


class TestDetection:
    """Tests for the core unused-default detection logic."""

    def test_default_never_used(
        self, project: Callable[[dict[str, str]], Path]
    ) -> None:
        root = project({"main.py": CODE_PROCESS_THREE_CALLS_EXPLICIT})
        issues = check(root)

        assert len(issues) == 1
        assert issues[0]["function"] == "process"
        assert issues[0]["param"] == "y"
        assert issues[0]["default"] == "10"
        assert issues[0]["call_sites"] == 3

    def test_default_sometimes_used(
        self, project: Callable[[dict[str, str]], Path]
    ) -> None:
        root = project({"main.py": CODE_PROCESS_MIXED_CALLS})
        issues = check(root)
        assert len(issues) == 0  # Default IS used, so no issue

    def test_keyword_argument(self, project: Callable[[dict[str, str]], Path]) -> None:
        root = project(
            {
                "main.py": """
def format_msg(text: str, prefix: str = "[INFO]") -> str:
    return f"{prefix} {text}"

a = format_msg("hello", prefix="[WARN]")
b = format_msg("world", prefix="[ERROR]")
"""
            }
        )
        issues = check(root)
        assert len(issues) == 1
        assert issues[0]["param"] == "prefix"

    def test_kwonly_param_never_used(
        self, project: Callable[[dict[str, str]], Path]
    ) -> None:
        root = project(
            {
                "main.py": """
def fetch(url: str, *, timeout: int = 30) -> str:
    return url

a = fetch("http://a.com", timeout=10)
b = fetch("http://b.com", timeout=20)
"""
            }
        )
        issues = check(root)
        assert len(issues) == 1
        assert issues[0]["param"] == "timeout"

    def test_kwonly_param_sometimes_used(
        self, project: Callable[[dict[str, str]], Path]
    ) -> None:
        root = project(
            {
                "main.py": """
def fetch(url: str, *, timeout: int = 30) -> str:
    return url

a = fetch("http://a.com")  # Uses default
b = fetch("http://b.com", timeout=20)
"""
            }
        )
        issues = check(root)
        assert len(issues) == 0

    def test_star_args_prevents_detection(
        self, project: Callable[[dict[str, str]], Path]
    ) -> None:
        """Can't statically determine if default is used with *args."""
        root = project(
            {
                "main.py": CODE_PROCESS
                + """
args = (1, 2)
a = process(*args)
"""
            }
        )
        issues = check(root)
        assert len(issues) == 0  # Conservative: don't flag if uncertain

    def test_double_star_kwargs_prevents_detection(
        self, project: Callable[[dict[str, str]], Path]
    ) -> None:
        """Can't statically determine if default is used with **kwargs."""
        root = project(
            {
                "main.py": CODE_PROCESS
                + """
kwargs = {"x": 1, "y": 2}
a = process(**kwargs)
"""
            }
        )
        issues = check(root)
        assert len(issues) == 0

    def test_multiple_files(self, project: Callable[[dict[str, str]], Path]) -> None:
        root = project(
            {
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
        )
        issues = check(root)
        assert len(issues) == 1
        assert issues[0]["function"] == "helper"
        assert issues[0]["param"] == "debug"

    def test_method_calls(self, project: Callable[[dict[str, str]], Path]) -> None:
        root = project(
            {
                "main.py": """
class Service:
    def process(self, x: int, y: int = 10) -> int:
        return x + y

s = Service()
a = s.process(1, 2)
b = s.process(3, 4)
"""
            }
        )
        issues = check(root)
        assert len(issues) == 1
        assert issues[0]["function"] == "process"
        assert issues[0]["param"] == "y"

    def test_none_default(self, project: Callable[[dict[str, str]], Path]) -> None:
        root = project(
            {
                "main.py": """
from typing import Optional

def get_config(path: str, fallback: Optional[str] = None) -> str:
    return fallback or path

a = get_config("/a", "/b")
b = get_config("/c", "/d")
"""
            }
        )
        issues = check(root)
        assert len(issues) == 1
        assert issues[0]["default"] == "None"

    def test_no_call_sites_no_issue(
        self, project: Callable[[dict[str, str]], Path]
    ) -> None:
        root = project({"lib.py": CODE_PROCESS})  # No calls
        issues = check(root)
        assert len(issues) == 0

    def test_private_functions_skipped(
        self, project: Callable[[dict[str, str]], Path]
    ) -> None:
        root = project(
            {
                "main.py": """
def _private(x: int, y: int = 10) -> int:
    return x + y

a = _private(1, 2)
b = _private(3, 4)
"""
            }
        )
        issues = check(root)
        assert len(issues) == 0  # Private functions are skipped

    def test_class_constructor_mixed_calls(
        self, project: Callable[[dict[str, str]], Path]
    ) -> None:
        root = project(
            {
                "main.py": """
class Foo:
    def __init__(self, x: int, y: int = 10) -> None:
        self.x = x
        self.y = y

a = Foo(1, 2)
b = Foo(3)  # Uses default
"""
            }
        )
        issues = check(root)
        assert len(issues) == 0

    def test_async_function(self, project: Callable[[dict[str, str]], Path]) -> None:
        root = project(
            {
                "main.py": """
async def fetch(url: str, timeout: int = 30) -> str:
    return url

import asyncio
asyncio.run(fetch("http://test.com", timeout=10))
"""
            }
        )
        issues = check(root)
        assert len(issues) == 1
        assert issues[0]["function"] == "fetch"
        assert issues[0]["param"] == "timeout"

    def test_kwonly_without_default(
        self, project: Callable[[dict[str, str]], Path]
    ) -> None:
        root = project(
            {
                "main.py": """
def process(x: int, *, required: str, optional: int = 10) -> int:
    return x

a = process(1, required="a", optional=5)
"""
            }
        )
        issues = check(root)
        assert len(issues) == 1
        assert issues[0]["param"] == "optional"

    def test_call_expression_callee(
        self, project: Callable[[dict[str, str]], Path]
    ) -> None:
        """Can't resolve callee when it's a call expression result."""
        root = project(
            {
                "main.py": """
def factory():
    def inner(x: int = 10):
        return x
    return inner

factory()(5)
"""
            }
        )
        issues = check(root)
        assert len(issues) == 0


# =============================================================================
# TESTS: Default Value Representations
# =============================================================================


class TestDefaultRepresentations:
    """Tests for how different default value types are represented."""

    def test_various_default_types(
        self, project: Callable[[dict[str, str]], Path]
    ) -> None:
        root = project(
            {
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
        )
        issues = check(root)
        assert len(issues) == 7

        defaults = {i["param"]: i["default"] for i in issues}
        assert defaults["a"] == "[...]"
        assert defaults["b"] == "{...}"
        assert defaults["c"] == "{...}"
        assert defaults["d"] == "(...)"
        assert defaults["e"] == "dict()"
        assert defaults["f"] == "lambda"
        assert defaults["g"] == "-1"

    def test_default_is_variable_name(
        self, project: Callable[[dict[str, str]], Path]
    ) -> None:
        root = project(
            {
                "main.py": """
DEFAULT_VALUE = 42

def func(x: int = DEFAULT_VALUE) -> int:
    return x

func(10)
func(20)
"""
            }
        )
        issues = check(root)
        assert len(issues) == 1
        assert issues[0]["default"] == "DEFAULT_VALUE"

    def test_default_is_method_call(
        self, project: Callable[[dict[str, str]], Path]
    ) -> None:
        root = project(
            {
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
        )
        issues = check(root)
        assert len(issues) == 1
        assert issues[0]["default"] == "<call>"

    def test_default_is_complex_expression(
        self, project: Callable[[dict[str, str]], Path]
    ) -> None:
        root = project(
            {
                "main.py": """
def func(x: int = 1 + 2) -> int:
    return x

func(10)
"""
            }
        )
        issues = check(root)
        assert len(issues) == 1
        assert issues[0]["default"] == "<expr>"


# =============================================================================
# TESTS: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Edge cases and special scenarios."""

    def test_syntax_error_file_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "good.py").write_text(
            """
def func(x: int = 10) -> int:
    return x

func(20)
"""
        )
        (tmp_path / "bad.py").write_text("def broken syntax")

        checker = UnusedDefaultsChecker(str(tmp_path), quiet=True)
        issues = checker.analyze()
        assert len(issues) == 1
        assert issues[0].function_name == "func"

    def test_hidden_directory_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "good.py").write_text(
            """
def func(x: int = 10) -> int:
    return x

func(20)
"""
        )
        hidden = tmp_path / ".hidden"
        hidden.mkdir()
        (hidden / "bad.py").write_text(
            """
def other(y: int = 20) -> int:
    return y

other(30)
"""
        )

        checker = UnusedDefaultsChecker(str(tmp_path), quiet=True)
        issues = checker.analyze()
        assert len(issues) == 1
        assert issues[0].function_name == "func"
