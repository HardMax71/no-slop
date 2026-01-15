
import ast

from no_slop.rules.flake8.base import IgnoreHandler
from no_slop.rules.flake8.idiomatic import check_idiomatic_patterns


class MockChecker:
    name = "no-slop"

class TestRedundantLoopGuarding:
    def test_redundant_guard_detected(self):
        code = """
if items:
    for item in items:
        pass
        """
        tree = ast.parse(code)
        ignores = IgnoreHandler(code.splitlines())
        errors = list(check_idiomatic_patterns(tree, ignores, MockChecker))

        assert len(errors) == 1
        assert "SLP601" in errors[0][2]

    def test_guard_with_else_ok(self):
        code = """
if items:
    for item in items:
        pass
else:
    print("empty")
        """
        tree = ast.parse(code)
        ignores = IgnoreHandler(code.splitlines())
        errors = list(check_idiomatic_patterns(tree, ignores, MockChecker))
        assert len(errors) == 0

    def test_guard_with_other_logic_ok(self):
        code = """
if items and active:
    for item in items:
        pass
        """
        tree = ast.parse(code)
        ignores = IgnoreHandler(code.splitlines())
        errors = list(check_idiomatic_patterns(tree, ignores, MockChecker))
        assert len(errors) == 0

class TestUnpythonicLoop:
    def test_range_len_detected(self):
        code = """
for i in range(len(items)):
    print(items[i])
        """
        tree = ast.parse(code)
        ignores = IgnoreHandler(code.splitlines())
        errors = list(check_idiomatic_patterns(tree, ignores, MockChecker))

        assert len(errors) == 1
        assert "SLP602" in errors[0][2]

    def test_range_len_no_indexing_ok(self):
        # If we don't index, maybe we just need the index?
        code = """
for i in range(len(items)):
    print(i)
        """
        tree = ast.parse(code)
        ignores = IgnoreHandler(code.splitlines())
        errors = list(check_idiomatic_patterns(tree, ignores, MockChecker))
        assert len(errors) == 0

    def test_enumerate_ok(self):
        code = """
for i, item in enumerate(items):
    print(item)
        """
        tree = ast.parse(code)
        ignores = IgnoreHandler(code.splitlines())
        errors = list(check_idiomatic_patterns(tree, ignores, MockChecker))
        assert len(errors) == 0
