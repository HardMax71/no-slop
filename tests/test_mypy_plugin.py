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
        assert "slop-isinstance" in output

    def test_isinstance_on_union_ok(self) -> None:
        code = """
def process(x: int | str) -> str:
    if isinstance(x, int):
        return str(x)
    return x
"""
        output = run_mypy_on_code(code)
        assert "slop-isinstance" not in output

    def test_isinstance_on_any_flagged(self) -> None:
        code = """
def process(data):
    if isinstance(data, dict):
        return data.get("key")
    return None
"""
        output = run_mypy_on_code(code)
        assert "slop-any-check" in output

    def test_isinstance_with_builtin_int(self) -> None:
        code = """
def process(x: int) -> str:
    if isinstance(x, int):
        return str(x)
    return ""
"""
        output = run_mypy_on_code(code)
        assert "slop-isinstance" in output

    def test_isinstance_with_tuple_of_types(self) -> None:
        code = """
from dataclasses import dataclass

@dataclass
class User:
    name: str

def process(user: User) -> str:
    if isinstance(user, (User, str)):
        return str(user)
    return ""
"""
        output = run_mypy_on_code(code)
        assert "slop-isinstance" in output

    def test_isinstance_subclass_detected(self) -> None:
        code = """
class Animal:
    pass

class Dog(Animal):
    pass

def process(dog: Dog) -> bool:
    return isinstance(dog, Animal)
"""
        output = run_mypy_on_code(code)
        assert "slop-isinstance" in output

    def test_isinstance_with_none_type(self) -> None:
        code = """
def process(x: None) -> bool:
    return isinstance(x, type(None))
"""
        output = run_mypy_on_code(code)
        assert "slop-isinstance" not in output


class TestHasattrChecks:
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
        assert "slop-any-check" not in output

    def test_hasattr_on_object_flagged(self) -> None:
        code = """
def process(data: object) -> str:
    if hasattr(data, "name"):
        return getattr(data, "name", "")
    return ""
"""
        output = run_mypy_on_code(code)
        assert "slop-any-check" in output

    def test_hasattr_inherited_attribute(self) -> None:
        code = """
class Base:
    name: str = "base"

class Child(Base):
    pass

def get_name(c: Child) -> str:
    if hasattr(c, "name"):
        return c.name
    return ""
"""
        output = run_mypy_on_code(code)
        assert "slop-hasattr" in output

    def test_hasattr_with_getattr_method(self) -> None:
        code = """
class Dynamic:
    def __getattr__(self, name: str) -> str:
        return name

def check(d: Dynamic) -> bool:
    return hasattr(d, "anything")
"""
        output = run_mypy_on_code(code)
        assert "slop-hasattr" not in output

    def test_hasattr_union_all_have_attr(self) -> None:
        code = """
class A:
    name: str = "a"

class B:
    name: str = "b"

def get_name(x: A | B) -> str:
    if hasattr(x, "name"):
        return x.name
    return ""
"""
        output = run_mypy_on_code(code)
        assert "slop-hasattr" in output


class TestGetattrChecks:
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
        assert "slop-getattr" not in output

    def test_getattr_on_any_flagged(self) -> None:
        code = """
def get_val(data) -> str:
    return getattr(data, "key", "default")
"""
        output = run_mypy_on_code(code)
        assert "slop-any-check" in output

    def test_getattr_inherited_attr(self) -> None:
        code = """
class Base:
    value: int = 42

class Child(Base):
    pass

def get_val(c: Child) -> int:
    return getattr(c, "value", 0)
"""
        output = run_mypy_on_code(code)
        assert "slop-getattr" in output


class TestCallableChecks:
    def test_redundant_callable(self) -> None:
        code = """
from typing import Callable

def invoke(func: Callable[[], int]) -> int:
    if callable(func):
        return func()
    return 0
"""
        output = run_mypy_on_code(code)
        assert "slop-callable" in output

    def test_callable_on_object_flagged(self) -> None:
        code = """
def call_maybe(func: object) -> int:
    if callable(func):
        return func()
    return 0
"""
        output = run_mypy_on_code(code)
        assert "slop-any-check" in output

    def test_callable_with_call_method(self) -> None:
        code = """
class Functor:
    def __call__(self) -> int:
        return 42

def invoke(f: Functor) -> int:
    if callable(f):
        return f()
    return 0
"""
        output = run_mypy_on_code(code)
        assert "slop-callable" in output

    def test_callable_on_class_type(self) -> None:
        code = """
class MyClass:
    pass

def create(cls: type[MyClass]) -> MyClass:
    if callable(cls):
        return cls()
    raise ValueError()
"""
        output = run_mypy_on_code(code)
        # type[X] is TypeType, not detected as callable by current impl
        assert "slop-callable" not in output

    def test_callable_union_all_callable(self) -> None:
        code = """
from typing import Callable

def invoke(f: Callable[[], int] | Callable[[], str]) -> int | str:
    if callable(f):
        return f()
    return 0
"""
        output = run_mypy_on_code(code)
        assert "slop-callable" in output


class TestIssubclassChecks:
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
        assert "slop-issubclass" in output

    def test_issubclass_on_any_flagged(self) -> None:
        code = """
def check(cls) -> bool:
    return issubclass(cls, dict)
"""
        output = run_mypy_on_code(code)
        assert "slop-any-check" in output

    def test_issubclass_with_tuple(self) -> None:
        code = """
class Animal:
    pass

class Dog(Animal):
    pass

def check(cls: type[Dog]) -> bool:
    return issubclass(cls, (Animal, str))
"""
        output = run_mypy_on_code(code)
        assert "slop-issubclass" in output

    def test_issubclass_inheritance_chain(self) -> None:
        code = """
class A:
    pass

class B(A):
    pass

class C(B):
    pass

def check(cls: type[C]) -> bool:
    return issubclass(cls, A)
"""
        output = run_mypy_on_code(code)
        assert "slop-issubclass" in output

    def test_issubclass_not_redundant(self) -> None:
        code = """
class A:
    pass

class B:
    pass

def check(cls: type[A] | type[B]) -> bool:
    return issubclass(cls, A)
"""
        output = run_mypy_on_code(code)
        assert "slop-issubclass" not in output


class TestIgnoreComments:
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
        assert "slop-hasattr" not in output

    def test_ignore_callable(self) -> None:
        code = """
from typing import Callable

def invoke(func: Callable[[], int]) -> int:
    if callable(func):  # type: ignore[slop-callable]
        return func()
    return 0
"""
        output = run_mypy_on_code(code)
        assert "slop-callable" not in output
