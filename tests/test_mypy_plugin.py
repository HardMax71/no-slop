"""Unit tests for the mypy plugin."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


def run_mypy_on_code(code: str, extra_args: list[str] | None = None) -> str:
    """Run mypy on a code snippet and return the output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Write the code file
        code_file = tmppath / "test_code.py"
        code_file.write_text(code)

        # Use the project's pyproject.toml for configuration
        project_config = Path(__file__).parent.parent / "pyproject.toml"

        cmd = [
            sys.executable,
            "-m",
            "mypy",
            "--config-file",
            str(project_config),
            "--no-error-summary",
            str(code_file),
        ]
        if extra_args:
            cmd.extend(extra_args)

        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout + result.stderr


class TestIsinstanceChecks:
    """Tests for redundant isinstance detection."""

    def test_redundant_isinstance_simple(self) -> None:
        code = """
from dataclasses import dataclass

@dataclass
class User:
    name: str

def process(user: User) -> str:
    if isinstance(user, User):
        return user.name
    return ""
"""
        output = run_mypy_on_code(code)
        assert "SLOP001" in output
        assert "slop-isinstance" in output

    def test_isinstance_on_union_ok(self) -> None:
        code = """
def process(x: int | str) -> str:
    if isinstance(x, int):
        return str(x)
    return x
"""
        output = run_mypy_on_code(code)
        assert "SLOP001" not in output
        assert "slop-isinstance" not in output

    def test_isinstance_on_any_flagged(self) -> None:
        code = """
def process(data):
    if isinstance(data, dict):
        return data.get("key")
    return None
"""
        output = run_mypy_on_code(code)
        assert "SLOP007" in output
        assert "slop-any-check" in output


class TestHasattrChecks:
    """Tests for redundant hasattr detection."""

    def test_redundant_hasattr(self) -> None:
        code = """
from dataclasses import dataclass

@dataclass
class User:
    name: str

def get_name(user: User) -> str:
    if hasattr(user, "name"):
        return user.name
    return ""
"""
        output = run_mypy_on_code(code)
        assert "SLOP003" in output
        assert "slop-hasattr" in output

    def test_hasattr_dynamic_attr_ok(self) -> None:
        code = """
def get_attr(obj: object, attr: str) -> object:
    if hasattr(obj, attr):
        return getattr(obj, attr)
    return None
"""
        output = run_mypy_on_code(code)
        # Dynamic attr string - can't analyze statically, no error
        # Plugin only checks literal strings
        assert "SLOP007" not in output

    def test_hasattr_on_object_flagged(self) -> None:
        code = """
def process(data: object) -> str:
    if hasattr(data, "name"):
        return getattr(data, "name", "")
    return ""
"""
        output = run_mypy_on_code(code)
        assert "SLOP007" in output


class TestGetattrChecks:
    """Tests for redundant getattr detection."""

    def test_redundant_getattr_with_default(self) -> None:
        code = """
from dataclasses import dataclass

@dataclass
class User:
    email: str

def get_email(user: User) -> str:
    return getattr(user, "email", "no-email")
"""
        output = run_mypy_on_code(code)
        assert "SLOP004" in output
        assert "slop-getattr" in output

    def test_getattr_without_default_ok(self) -> None:
        code = """
from dataclasses import dataclass

@dataclass
class User:
    email: str

def get_email(user: User) -> str:
    return getattr(user, "email")
"""
        output = run_mypy_on_code(code)
        # Without default, no SLOP004 warning
        assert "SLOP004" not in output


class TestCallableChecks:
    """Tests for redundant callable detection."""

    def test_redundant_callable(self) -> None:
        code = """
from typing import Callable

def invoke(func: Callable[[], int]) -> int:
    if callable(func):
        return func()
    return 0
"""
        output = run_mypy_on_code(code)
        assert "SLOP005" in output
        assert "slop-callable" in output

    def test_callable_on_object_flagged(self) -> None:
        code = """
def call_maybe(func: object) -> int:
    if callable(func):
        return func()
    return 0
"""
        output = run_mypy_on_code(code)
        assert "SLOP007" in output


class TestIssubclassChecks:
    """Tests for redundant issubclass detection."""

    def test_redundant_issubclass(self) -> None:
        code = """
from dataclasses import dataclass

@dataclass
class User:
    name: str

def check_class(cls: type[User]) -> bool:
    return issubclass(cls, User)
"""
        output = run_mypy_on_code(code)
        assert "SLOP002" in output
        assert "slop-issubclass" in output


class TestIgnoreComments:
    """Tests for type: ignore comments."""

    def test_ignore_hasattr(self) -> None:
        code = """
from dataclasses import dataclass

@dataclass
class User:
    name: str

def get_name(user: User) -> str:
    if hasattr(user, "name"):  # type: ignore[slop-hasattr]
        return user.name
    return ""
"""
        output = run_mypy_on_code(code)
        assert "SLOP003" not in output

    def test_ignore_callable(self) -> None:
        code = """
from typing import Callable

def invoke(func: Callable[[], int]) -> int:
    if callable(func):  # type: ignore[slop-callable]
        return func()
    return 0
"""
        output = run_mypy_on_code(code)
        assert "SLOP005" not in output
