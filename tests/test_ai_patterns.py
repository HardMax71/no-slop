import ast

from no_slop.flake8_plugin import SlopStyleChecker


def check_code(
    code: str, filename: str = "test.py"
) -> list[tuple[int, int, str, type]]:
    lines = code.splitlines()
    tree = ast.parse(code)
    checker = SlopStyleChecker(tree, lines, filename)
    return list(checker.run())


class TestPlaceholderBodies:
    def test_placeholder_function_detected(self) -> None:
        code = """
def build():
    pass
"""
        errors = check_code(code)
        slp033 = [e for e in errors if "SLP033" in e[2]]
        assert len(slp033) == 1

    def test_placeholder_class_detected(self) -> None:
        code = """
class Thing:
    ...
"""
        errors = check_code(code)
        slp033 = [e for e in errors if "SLP033" in e[2]]
        assert len(slp033) == 1

    def test_docstring_only_ok(self) -> None:
        code = '''
def explain():
    """Doc only."""
'''
        errors = check_code(code)
        slp033 = [e for e in errors if "SLP033" in e[2]]
        assert len(slp033) == 0

    def test_abstractmethod_ignored(self) -> None:
        code = """
from abc import ABC, abstractmethod

class Base(ABC):
    @abstractmethod
    def run(self):
        pass
"""
        errors = check_code(code)
        slp033 = [e for e in errors if "SLP033" in e[2]]
        assert len(slp033) == 0

    def test_protocol_ignored(self) -> None:
        code = """
from typing import Protocol

class Runner(Protocol):
    def run(self) -> int:
        ...
"""
        errors = check_code(code)
        slp033 = [e for e in errors if "SLP033" in e[2]]
        assert len(slp033) == 0


class TestPlaceholderComments:
    def test_todo_comment_detected(self) -> None:
        code = """
# TODO: implement this
value = 1
"""
        errors = check_code(code)
        slp034 = [e for e in errors if "SLP034" in e[2]]
        assert len(slp034) == 1

    def test_noqa_ignored(self) -> None:
        code = """
# TODO: finish this  # noqa: SLP034
value = 1
"""
        errors = check_code(code)
        slp034 = [e for e in errors if "SLP034" in e[2]]
        assert len(slp034) == 0

    def test_tracked_todo_ok(self) -> None:
        code = """
# TODO: handle edge cases (PROJ-123)
value = 1
"""
        errors = check_code(code)
        slp034 = [e for e in errors if "SLP034" in e[2]]
        assert len(slp034) == 0

    def test_placeholder_body_context_detected(self) -> None:
        code = """
def build():
    # TODO
    pass
"""
        errors = check_code(code)
        slp034 = [e for e in errors if "SLP034" in e[2]]
        assert len(slp034) == 1


class TestDebugArtifacts:
    def test_print_detected(self) -> None:
        code = """
def run():
    print("hi")
"""
        errors = check_code(code)
        slp035 = [e for e in errors if "SLP035" in e[2]]
        assert len(slp035) == 1

    def test_debug_guard_allowed(self) -> None:
        code = """
if __debug__:
    print("hi")
"""
        errors = check_code(code)
        slp035 = [e for e in errors if "SLP035" in e[2]]
        assert len(slp035) == 0

    def test_tests_path_allowed(self) -> None:
        code = """
def run():
    print("hi")
"""
        errors = check_code(code, filename="tests/test_debug.py")
        slp035 = [e for e in errors if "SLP035" in e[2]]
        assert len(slp035) == 0


class TestCrossLanguageAPIs:
    def test_js_list_method_detected(self) -> None:
        code = """
items: list[int] = []
items.push(1)
"""
        errors = check_code(code)
        slp036 = [e for e in errors if "SLP036" in e[2]]
        assert len(slp036) == 1

    def test_valid_list_method_ok(self) -> None:
        code = """
items = []
items.append(1)
"""
        errors = check_code(code)
        slp036 = [e for e in errors if "SLP036" in e[2]]
        assert len(slp036) == 0

    def test_string_length_detected(self) -> None:
        code = """
name: str = "abc"
size = name.length
"""
        errors = check_code(code)
        slp036 = [e for e in errors if "SLP036" in e[2]]
        assert len(slp036) == 1

    def test_sequence_push_detected(self) -> None:
        code = """
from typing import Sequence

items: Sequence[int] = [1, 2]
items.push(1)
"""
        errors = check_code(code)
        slp036 = [e for e in errors if "SLP036" in e[2]]
        assert len(slp036) == 1


class TestHallucinatedImports:
    def test_missing_import_detected(self) -> None:
        code = "import missing_slop_pkg_12345"
        errors = check_code(code)
        slp037 = [e for e in errors if "SLP037" in e[2]]
        assert len(slp037) == 1

    def test_standard_lib_ok(self) -> None:
        code = "import os"
        errors = check_code(code)
        slp037 = [e for e in errors if "SLP037" in e[2]]
        assert len(slp037) == 0

    def test_declared_dependency_ok(self) -> None:
        code = "import mypy"
        errors = check_code(code)
        slp037 = [e for e in errors if "SLP037" in e[2]]
        assert len(slp037) == 0

    def test_try_importerror_ignored(self) -> None:
        code = """
try:
    import missing_slop_pkg_12345
except ImportError:
    pass
"""
        errors = check_code(code)
        slp037 = [e for e in errors if "SLP037" in e[2]]
        assert len(slp037) == 0

    def test_type_checking_ignored(self) -> None:
        code = """
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import missing_slop_pkg_12345
"""
        errors = check_code(code)
        slp037 = [e for e in errors if "SLP037" in e[2]]
        assert len(slp037) == 0

    def test_relative_import_ignored(self) -> None:
        code = "from . import local"
        errors = check_code(code)
        slp037 = [e for e in errors if "SLP037" in e[2]]
        assert len(slp037) == 0


class TestHedgingComments:
    def test_hedging_comment_detected(self) -> None:
        code = """
# This should work for now
value = 1
"""
        errors = check_code(code)
        slp038 = [e for e in errors if "SLP038" in e[2]]
        assert len(slp038) == 1

    def test_hedging_docstring_detected(self) -> None:
        code = '''
def run() -> int:
    """This should work."""
    return 1
'''
        errors = check_code(code)
        slp038 = [e for e in errors if "SLP038" in e[2]]
        assert len(slp038) == 1


class TestSingleMethodClass:
    def test_wrapper_detected(self) -> None:
        code = """
class Wrapper:
    def __init__(self, value):
        self.value = value

    def run(self):
        return self.value
"""
        errors = check_code(code)
        slp039 = [e for e in errors if "SLP039" in e[2]]
        assert len(slp039) == 1

    def test_with_base_ok(self) -> None:
        code = """
class Wrapper(Base):
    def run(self):
        return 1
"""
        errors = check_code(code)
        slp039 = [e for e in errors if "SLP039" in e[2]]
        assert len(slp039) == 0

    def test_class_var_ok(self) -> None:
        code = """
class Wrapper:
    scale = 1

    def run(self):
        return 1
"""
        errors = check_code(code)
        slp039 = [e for e in errors if "SLP039" in e[2]]
        assert len(slp039) == 0


class TestFunctionComplexity:
    def test_deep_nesting_detected(self) -> None:
        code = """
def deep(value):
    if value:
        if value:
            if value:
                if value:
                    if value:
                        x = 1
"""
        errors = check_code(code)
        slp040 = [e for e in errors if "SLP040" in e[2]]
        assert len(slp040) == 1

    def test_long_function_detected(self) -> None:
        lines = ["def big(value):"]
        for i in range(85):
            lines.append(f"    x = {i}")
        code = "\n".join(lines)
        errors = check_code(code)
        slp040 = [e for e in errors if "SLP040" in e[2]]
        assert len(slp040) == 1
