from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from no_slop.flake8_plugin import SlopStyleChecker

if TYPE_CHECKING:
    pass


def check_code(code: str) -> list[tuple[int, int, str, type]]:
    lines = code.splitlines()
    tree = ast.parse(code)
    checker = SlopStyleChecker(tree, lines, "test.py")
    return list(checker.run())


class TestEmojiDetection:
    def test_emoji_in_string(self) -> None:
        code = 'x = "Hello 🎉 World"'
        errors = check_code(code)
        assert len(errors) == 1
        assert "SLP022" in errors[0][2]
        assert "🎉" in errors[0][2]

    def test_emoji_in_comment(self) -> None:
        code = "x = 1  # 🚀 rocket ship"
        errors = check_code(code)
        assert len(errors) == 1
        assert "SLP022" in errors[0][2]

    def test_multiple_emojis(self) -> None:
        code = 'msg = "🎯 ✨ 🎉"'
        errors = check_code(code)
        assert len(errors) == 1
        # All emojis should be listed
        assert "🎯" in errors[0][2]
        assert "✨" in errors[0][2]
        assert "🎉" in errors[0][2]

    def test_no_emoji_clean(self) -> None:
        code = 'x = "Hello World"'
        errors = check_code(code)
        emoji_errors = [e for e in errors if "SLP022" in e[2]]
        assert len(emoji_errors) == 0

    def test_emoji_ignored_with_noqa(self) -> None:
        code = 'x = "Hello 🎉"  # noqa: SLP022'
        errors = check_code(code)
        assert len(errors) == 0

    def test_emoji_ignored_with_noqa_all(self) -> None:
        code = 'x = "Hello 🎉"  # noqa'
        errors = check_code(code)
        assert len(errors) == 0


class TestAsciiArtDetection:
    def test_box_drawing(self) -> None:
        code = "# ╔════════════════════════╗"
        errors = check_code(code)
        assert len(errors) == 1
        assert "SLP021" in errors[0][2]
        assert "Box-drawing" in errors[0][2]

    def test_block_characters(self) -> None:
        code = "# ████████████████████████"
        errors = check_code(code)
        assert len(errors) == 1
        assert "SLP021" in errors[0][2]
        assert "Block-drawing" in errors[0][2]

    def test_simple_separator_allowed(self) -> None:
        code = "# ========================================="
        errors = check_code(code)
        # Simple separators should be allowed
        art_errors = [e for e in errors if "SLP021" in e[2]]
        assert len(art_errors) == 0

    def test_section_header_allowed(self) -> None:
        code = "# === CONFIGURATION ==="
        errors = check_code(code)
        art_errors = [e for e in errors if "SLP021" in e[2]]
        assert len(art_errors) == 0

    def test_section_header_end_allowed(self) -> None:
        code = "# IMPORTS ============"
        errors = check_code(code)
        art_errors = [e for e in errors if "SLP021" in e[2]]
        assert len(art_errors) == 0

    def test_arrow_pattern_detected(self) -> None:
        code = "# <<<<<<<<<<<<<<<<<<<<<<<<<"
        errors = check_code(code)
        assert len(errors) == 1
        assert "SLP021" in errors[0][2]
        assert "arrow" in errors[0][2].lower()

    def test_caret_arrow_pattern_detected(self) -> None:
        code = "# ^^^^^^^^^^^^^^^^^^^^^^"
        errors = check_code(code)
        assert len(errors) == 1
        assert "SLP021" in errors[0][2]

    def test_ascii_art_ignored_with_noqa(self) -> None:
        code = "# ╔════════════════════════╗  # noqa: SLP021"
        errors = check_code(code)
        assert len(errors) == 0


class TestExcessiveDocstring:
    def test_long_docstring_flagged(self) -> None:
        docstring = '"""' + "\n".join(["Line " + str(i) for i in range(20)]) + '"""'
        code = f"""{docstring}

def foo() -> int:
    return 1
"""
        errors = check_code(code)
        docstring_errors = [e for e in errors if "SLP020" in e[2]]
        assert len(docstring_errors) == 1

    def test_short_docstring_ok(self) -> None:
        code = '''"""Short module docstring."""

def foo() -> int:
    return 1
'''
        errors = check_code(code)
        docstring_errors = [e for e in errors if "SLP020" in e[2]]
        assert len(docstring_errors) == 0

    def test_expression_not_constant_ok(self) -> None:
        code = """foo()

def bar() -> int:
    return 1
"""
        errors = check_code(code)
        docstring_errors = [e for e in errors if "SLP020" in e[2]]
        assert len(docstring_errors) == 0

    def test_constant_not_string_ok(self) -> None:
        code = """42

def bar() -> int:
    return 1
"""
        errors = check_code(code)
        docstring_errors = [e for e in errors if "SLP020" in e[2]]
        assert len(docstring_errors) == 0

    def test_docstring_with_statements_only(self) -> None:
        docstring = '"""' + "\n".join(["Line " + str(i) for i in range(20)]) + '"""'
        code = f"""{docstring}

x = 1
y = 2
z = 3
"""
        errors = check_code(code)
        docstring_errors = [e for e in errors if "SLP020" in e[2]]
        assert len(docstring_errors) == 1


class TestLeadingComments:
    def test_excessive_leading_comments(self) -> None:
        comments = "\n".join([f"# Comment line {i}" for i in range(15)])
        code = f"""{comments}

def foo() -> int:
    return 1
"""
        errors = check_code(code)
        comment_errors = [e for e in errors if "SLP020" in e[2]]
        assert len(comment_errors) == 1

    def test_short_leading_comments_ok(self) -> None:
        code = """# Author: Test
# License: MIT

def foo() -> int:
    return 1
"""
        errors = check_code(code)
        comment_errors = [e for e in errors if "SLP020" in e[2]]
        assert len(comment_errors) == 0


class TestFileIgnores:
    def test_file_ignore_all(self) -> None:
        code = """# slop: ignore-file
x = "🎉 Hello"  # Would be flagged
# ╔════════╗  # Would be flagged
"""
        errors = check_code(code)
        assert len(errors) == 0

    def test_file_ignore_specific_code(self) -> None:
        code = """# slop: ignore-file[SLP022]
x = "🎉 Hello"  # Emoji ignored
# ╔════════╗  # ASCII art NOT ignored
"""
        errors = check_code(code)
        emoji_errors = [e for e in errors if "SLP022" in e[2]]
        art_errors = [e for e in errors if "SLP021" in e[2]]
        assert len(emoji_errors) == 0
        assert len(art_errors) == 1

    def test_file_ignore_multiple_codes(self) -> None:
        code = """# slop: ignore-file[SLP021, SLP022]
x = "🎉 Hello"  # Ignored
# ╔════════╗  # Ignored
"""
        errors = check_code(code)
        assert len(errors) == 0


class TestMultipleIgnoreCodes:
    def test_multiple_codes_in_noqa(self) -> None:
        code = 'x = "🎉"  # ╔══╗ noqa: SLP021, SLP022'
        errors = check_code(code)
        assert len(errors) == 0

    def test_noqa_with_other_content(self) -> None:
        code = 'x = "🎉"  # TODO: fix this noqa: SLP022'
        errors = check_code(code)
        emoji_errors = [e for e in errors if "SLP022" in e[2]]
        assert len(emoji_errors) == 0


class TestLocalImports:
    def test_local_import_detected(self) -> None:
        code = """
def foo():
    import os
    return os.getcwd()
"""
        errors = check_code(code)
        local_errors = [e for e in errors if "SLP023" in e[2]]
        assert len(local_errors) == 1
        assert "Local import" in local_errors[0][2]

    def test_local_from_import_detected(self) -> None:
        code = """
def foo():
    from os import path
    return path.exists(".")
"""
        errors = check_code(code)
        local_errors = [e for e in errors if "SLP023" in e[2]]
        assert len(local_errors) == 1
        assert "from os import path" in local_errors[0][2]

    def test_module_level_import_ok(self) -> None:
        code = """
import os

def foo():
    return os.getcwd()
"""
        errors = check_code(code)
        local_errors = [e for e in errors if "SLP023" in e[2]]
        assert len(local_errors) == 0

    def test_type_checking_import_ok(self) -> None:
        code = """
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

def foo(x: "Sequence[int]") -> int:
    return x[0]
"""
        errors = check_code(code)
        local_errors = [e for e in errors if "SLP023" in e[2]]
        assert len(local_errors) == 0

    def test_type_checking_attribute_import_ok(self) -> None:
        code = """
import typing

if typing.TYPE_CHECKING:
    from collections.abc import Sequence

def foo(x: "Sequence[int]") -> int:
    return x[0]
"""
        errors = check_code(code)
        local_errors = [e for e in errors if "SLP023" in e[2]]
        assert len(local_errors) == 0

    def test_local_import_ignored_with_noqa(self) -> None:
        code = """
def foo():
    import os  # noqa: SLP023
    return os.getcwd()
"""
        errors = check_code(code)
        local_errors = [e for e in errors if "SLP023" in e[2]]
        assert len(local_errors) == 0

    def test_nested_function_local_import(self) -> None:
        code = """
def outer():
    def inner():
        import json
        return json.dumps({})
    return inner()
"""
        errors = check_code(code)
        local_errors = [e for e in errors if "SLP023" in e[2]]
        assert len(local_errors) == 1

    def test_async_function_local_import(self) -> None:
        code = """
async def fetch():
    import aiohttp
    return aiohttp
"""
        errors = check_code(code)
        local_errors = [e for e in errors if "SLP023" in e[2]]
        assert len(local_errors) == 1

    def test_class_method_local_import(self) -> None:
        code = """
class Foo:
    def bar(self):
        import sys
        return sys.version
"""
        errors = check_code(code)
        local_errors = [e for e in errors if "SLP023" in e[2]]
        assert len(local_errors) == 1

    def test_regular_if_block_visited(self) -> None:
        code = """
if True:
    x = 1

def foo():
    import os
    return os.getcwd()
"""
        errors = check_code(code)
        local_errors = [e for e in errors if "SLP023" in e[2]]
        assert len(local_errors) == 1

    def test_if_with_other_condition_not_type_checking(self) -> None:
        code = """
DEBUG = True
if DEBUG:
    from collections.abc import Sequence

def foo():
    import os
    return os.getcwd()
"""
        errors = check_code(code)
        local_errors = [e for e in errors if "SLP023" in e[2]]
        assert len(local_errors) == 1


class TestIndirectAccessPatterns:
    """Tests for SLP401-SLP407 indirect attribute access patterns."""

    def test_dict_get_detected(self) -> None:
        code = """
class User:
    name: str = ""

def get_name(user):
    return user.__dict__.get("name", "")
"""
        errors = check_code(code)
        slp401_errors = [e for e in errors if "SLP401" in e[2]]
        assert len(slp401_errors) == 1
        assert "__dict__.get()" in slp401_errors[0][2]

    def test_dict_subscript_read_detected(self) -> None:
        code = """
def get_name(user):
    return user.__dict__["name"]
"""
        errors = check_code(code)
        slp402_errors = [e for e in errors if "SLP402" in e[2]]
        assert len(slp402_errors) == 1

    def test_dict_subscript_write_detected(self) -> None:
        code = """
def set_name(user):
    user.__dict__["name"] = "John"
"""
        errors = check_code(code)
        slp403_errors = [e for e in errors if "SLP403" in e[2]]
        assert len(slp403_errors) == 1

    def test_dict_update_detected(self) -> None:
        code = """
def update_user(user):
    user.__dict__.update({"name": "John"})
"""
        errors = check_code(code)
        slp404_errors = [e for e in errors if "SLP404" in e[2]]
        assert len(slp404_errors) == 1

    def test_vars_get_detected(self) -> None:
        code = """
def get_name(user):
    return vars(user).get("name", "")
"""
        errors = check_code(code)
        slp405_errors = [e for e in errors if "SLP405" in e[2]]
        assert len(slp405_errors) == 1

    def test_vars_subscript_write_detected(self) -> None:
        code = """
def set_name(user):
    vars(user)["name"] = "John"
"""
        errors = check_code(code)
        slp406_errors = [e for e in errors if "SLP406" in e[2]]
        assert len(slp406_errors) == 1

    def test_asdict_get_detected(self) -> None:
        code = """
from dataclasses import asdict

def get_name(user):
    return asdict(user).get("name", "")
"""
        errors = check_code(code)
        slp407_errors = [e for e in errors if "SLP407" in e[2]]
        assert len(slp407_errors) == 1

    def test_asdict_alias_detected(self) -> None:
        code = """
from dataclasses import asdict as to_dict

def get_name(user):
    return to_dict(user).get("name", "")
"""
        errors = check_code(code)
        slp407_errors = [e for e in errors if "SLP407" in e[2]]
        assert len(slp407_errors) == 1

    def test_dynamic_key_not_detected(self) -> None:
        code = """
def get_attr(user, key):
    return user.__dict__.get(key, "")
"""
        errors = check_code(code)
        slp401_errors = [e for e in errors if "SLP401" in e[2]]
        assert len(slp401_errors) == 0

    def test_regular_dict_get_not_detected(self) -> None:
        code = """
def get_val(d: dict):
    return d.get("key", "")
"""
        errors = check_code(code)
        indirect_errors = [e for e in errors if e[2].startswith("SLP4")]
        assert len(indirect_errors) == 0

    def test_dict_get_ignored_with_noqa(self) -> None:
        code = """
def get_name(user):
    return user.__dict__.get("name", "")  # noqa: SLP401
"""
        errors = check_code(code)
        slp401_errors = [e for e in errors if "SLP401" in e[2]]
        assert len(slp401_errors) == 0

    def test_vars_without_get_not_detected(self) -> None:
        code = """
def show_attrs(user):
    print(vars(user))
"""
        errors = check_code(code)
        indirect_errors = [e for e in errors if e[2].startswith("SLP4")]
        assert len(indirect_errors) == 0

    def test_chained_dict_get_detected(self) -> None:
        code = """
def get_inner_name(obj):
    return obj.inner.__dict__.get("name", "")
"""
        errors = check_code(code)
        slp401_errors = [e for e in errors if "SLP401" in e[2]]
        assert len(slp401_errors) == 1


class TestDictGetKnownKey:
    """Tests for SLP408 - .get() on dict with known keys."""

    def test_inline_dict_literal_get(self) -> None:
        code = """
x = {"a": 1, "b": 2}.get("a", 0)
"""
        errors = check_code(code)
        slp408_errors = [e for e in errors if "SLP408" in e[2]]
        assert len(slp408_errors) == 1
        assert "'a'" in slp408_errors[0][2]

    def test_inline_dict_constructor_get(self) -> None:
        code = """
x = dict(host="localhost", port=8080).get("host", "default")
"""
        errors = check_code(code)
        slp408_errors = [e for e in errors if "SLP408" in e[2]]
        assert len(slp408_errors) == 1
        assert "'host'" in slp408_errors[0][2]

    def test_variable_dict_literal_get(self) -> None:
        code = """
config = {"host": "localhost", "port": 8080}
result = config.get("host", "default")
"""
        errors = check_code(code)
        slp408_errors = [e for e in errors if "SLP408" in e[2]]
        assert len(slp408_errors) == 1

    def test_variable_dict_constructor_get(self) -> None:
        code = """
config = dict(host="localhost", port=8080)
result = config.get("host", "default")
"""
        errors = check_code(code)
        slp408_errors = [e for e in errors if "SLP408" in e[2]]
        assert len(slp408_errors) == 1

    def test_no_default_not_detected(self) -> None:
        code = """
d = {"a": 1}
x = d.get("a")
"""
        errors = check_code(code)
        slp408_errors = [e for e in errors if "SLP408" in e[2]]
        assert len(slp408_errors) == 0

    def test_unknown_key_not_detected(self) -> None:
        code = """
d = {"a": 1}
x = d.get("b", 0)
"""
        errors = check_code(code)
        slp408_errors = [e for e in errors if "SLP408" in e[2]]
        assert len(slp408_errors) == 0

    def test_after_pop_not_detected(self) -> None:
        code = """
d = {"a": 1}
d.pop("a")
x = d.get("a", 0)
"""
        errors = check_code(code)
        slp408_errors = [e for e in errors if "SLP408" in e[2]]
        assert len(slp408_errors) == 0

    def test_after_clear_not_detected(self) -> None:
        code = """
d = {"a": 1}
d.clear()
x = d.get("a", 0)
"""
        errors = check_code(code)
        slp408_errors = [e for e in errors if "SLP408" in e[2]]
        assert len(slp408_errors) == 0

    def test_after_del_not_detected(self) -> None:
        code = """
d = {"a": 1}
del d["a"]
x = d.get("a", 0)
"""
        errors = check_code(code)
        slp408_errors = [e for e in errors if "SLP408" in e[2]]
        assert len(slp408_errors) == 0

    def test_after_reassignment_not_detected(self) -> None:
        code = """
d = {"a": 1}
d = other_dict()
x = d.get("a", 0)
"""
        errors = check_code(code)
        slp408_errors = [e for e in errors if "SLP408" in e[2]]
        assert len(slp408_errors) == 0

    def test_dict_with_inner_dict_arg(self) -> None:
        code = """
d = dict({"a": 1, "b": 2})
x = d.get("a", 0)
"""
        errors = check_code(code)
        slp408_errors = [e for e in errors if "SLP408" in e[2]]
        assert len(slp408_errors) == 1

    def test_ignored_with_noqa(self) -> None:
        code = """
d = {"a": 1}
x = d.get("a", 0)  # noqa: SLP408
"""
        errors = check_code(code)
        slp408_errors = [e for e in errors if "SLP408" in e[2]]
        assert len(slp408_errors) == 0


class TestUnnecessaryElse:
    """Tests for SLP501 - Unnecessary else after return/raise/break/continue."""

    def test_else_after_return_with_multiple_stmts_detected(self) -> None:
        code = """
def foo(x):
    if x > 0:
        return 1
    else:
        log("taking else path")
        return 0
"""
        errors = check_code(code)
        slp501_errors = [e for e in errors if "SLP501" in e[2]]
        assert len(slp501_errors) == 1

    def test_else_after_raise_with_multiple_stmts_detected(self) -> None:
        code = """
def foo(x):
    if x < 0:
        raise ValueError("negative")
    else:
        log("ok")
        return x
"""
        errors = check_code(code)
        slp501_errors = [e for e in errors if "SLP501" in e[2]]
        assert len(slp501_errors) == 1

    def test_single_return_in_else_ok(self) -> None:
        # Single return in else is a valid, clear pattern
        code = """
def foo(x):
    if x > 0:
        return 1
    else:
        return 0
"""
        errors = check_code(code)
        slp501_errors = [e for e in errors if "SLP501" in e[2]]
        assert len(slp501_errors) == 0

    def test_elif_not_flagged(self) -> None:
        code = """
def foo(x):
    if x < 0:
        return -1
    elif x > 0:
        return 1
    else:
        return 0
"""
        errors = check_code(code)
        slp501_errors = [e for e in errors if "SLP501" in e[2]]
        # elif chains are acceptable
        assert len(slp501_errors) == 0

    def test_else_without_jump_ok(self) -> None:
        code = """
def foo(x):
    if x > 0:
        y = 1
    else:
        y = 0
    return y
"""
        errors = check_code(code)
        slp501_errors = [e for e in errors if "SLP501" in e[2]]
        assert len(slp501_errors) == 0

    def test_else_after_break_detected(self) -> None:
        code = """
def foo():
    for i in range(10):
        if i == 5:
            break
        else:
            print(i)
"""
        errors = check_code(code)
        slp501_errors = [e for e in errors if "SLP501" in e[2]]
        assert len(slp501_errors) == 1

    def test_ignored_with_noqa(self) -> None:
        code = """
def foo():
    for i in range(10):
        if i == 5:  # noqa: SLP501
            break
        else:
            print(i)
"""
        errors = check_code(code)
        slp501_errors = [e for e in errors if "SLP501" in e[2]]
        assert len(slp501_errors) == 0


class TestRedundantBooleanComparisons:
    """Tests for SLP502 - Redundant boolean comparisons."""

    def test_eq_true_detected(self) -> None:
        code = """
if x == True:
    pass
"""
        errors = check_code(code)
        slp502_errors = [e for e in errors if "SLP502" in e[2]]
        assert len(slp502_errors) == 1
        assert "if x" in slp502_errors[0][2]

    def test_eq_false_detected(self) -> None:
        code = """
if x == False:
    pass
"""
        errors = check_code(code)
        slp502_errors = [e for e in errors if "SLP502" in e[2]]
        assert len(slp502_errors) == 1
        assert "if not x" in slp502_errors[0][2]

    def test_eq_none_detected(self) -> None:
        code = """
if x == None:
    pass
"""
        errors = check_code(code)
        slp502_errors = [e for e in errors if "SLP502" in e[2]]
        assert len(slp502_errors) == 1
        assert "is None" in slp502_errors[0][2]

    def test_ne_none_detected(self) -> None:
        code = """
if x != None:
    pass
"""
        errors = check_code(code)
        slp502_errors = [e for e in errors if "SLP502" in e[2]]
        assert len(slp502_errors) == 1
        assert "is not None" in slp502_errors[0][2]

    def test_len_eq_zero_detected(self) -> None:
        code = """
if len(items) == 0:
    pass
"""
        errors = check_code(code)
        slp502_errors = [e for e in errors if "SLP502" in e[2]]
        assert len(slp502_errors) == 1
        assert "if not x" in slp502_errors[0][2]

    def test_len_gt_zero_detected(self) -> None:
        code = """
if len(items) > 0:
    pass
"""
        errors = check_code(code)
        slp502_errors = [e for e in errors if "SLP502" in e[2]]
        assert len(slp502_errors) == 1
        assert "if x" in slp502_errors[0][2]

    def test_is_true_ok(self) -> None:
        code = """
if x is True:
    pass
"""
        errors = check_code(code)
        slp502_errors = [e for e in errors if "SLP502" in e[2]]
        # 'is True' is intentional for exact True match
        assert len(slp502_errors) == 0

    def test_is_none_ok(self) -> None:
        code = """
if x is None:
    pass
"""
        errors = check_code(code)
        slp502_errors = [e for e in errors if "SLP502" in e[2]]
        assert len(slp502_errors) == 0

    def test_ignored_with_noqa(self) -> None:
        code = """
if x == True:  # noqa: SLP502
    pass
"""
        errors = check_code(code)
        slp502_errors = [e for e in errors if "SLP502" in e[2]]
        assert len(slp502_errors) == 0


class TestUnnecessaryPass:
    """Tests for SLP503 - Unnecessary pass in non-empty block."""

    def test_pass_with_code_detected(self) -> None:
        code = """
def foo():
    x = 1
    pass
"""
        errors = check_code(code)
        slp503_errors = [e for e in errors if "SLP503" in e[2]]
        assert len(slp503_errors) == 1

    def test_pass_only_ok(self) -> None:
        code = """
def foo():
    pass
"""
        errors = check_code(code)
        slp503_errors = [e for e in errors if "SLP503" in e[2]]
        assert len(slp503_errors) == 0

    def test_pass_in_class_detected(self) -> None:
        code = """
class Foo:
    x: int = 1
    pass
"""
        errors = check_code(code)
        slp503_errors = [e for e in errors if "SLP503" in e[2]]
        assert len(slp503_errors) == 1

    def test_pass_in_except_detected(self) -> None:
        code = """
try:
    foo()
except ValueError:
    log_error()
    pass
"""
        errors = check_code(code)
        slp503_errors = [e for e in errors if "SLP503" in e[2]]
        assert len(slp503_errors) == 1


class TestBareExcept:
    """Tests for SLP504 - Bare except and exception swallowing."""

    def test_bare_except_detected(self) -> None:
        code = """
try:
    foo()
except:
    pass
"""
        errors = check_code(code)
        slp504_errors = [e for e in errors if "SLP504" in e[2]]
        assert len(slp504_errors) == 1
        assert "Bare except" in slp504_errors[0][2]

    def test_exception_swallow_detected(self) -> None:
        code = """
try:
    foo()
except Exception:
    pass
"""
        errors = check_code(code)
        slp504_errors = [e for e in errors if "SLP504" in e[2]]
        assert len(slp504_errors) == 1
        assert "swallowed" in slp504_errors[0][2]

    def test_specific_exception_ok(self) -> None:
        code = """
try:
    foo()
except ValueError:
    pass
"""
        errors = check_code(code)
        slp504_errors = [e for e in errors if "SLP504" in e[2]]
        assert len(slp504_errors) == 0

    def test_exception_with_handling_ok(self) -> None:
        code = """
try:
    foo()
except Exception:
    log_error()
"""
        errors = check_code(code)
        slp504_errors = [e for e in errors if "SLP504" in e[2]]
        assert len(slp504_errors) == 0

    def test_ignored_with_noqa(self) -> None:
        code = """
try:
    foo()
except:  # noqa: SLP504
    pass
"""
        errors = check_code(code)
        slp504_errors = [e for e in errors if "SLP504" in e[2]]
        assert len(slp504_errors) == 0


class TestMutableDefaults:
    """Tests for SLP505 - Mutable default arguments."""

    def test_list_default_detected(self) -> None:
        code = """
def foo(items=[]):
    return items
"""
        errors = check_code(code)
        slp505_errors = [e for e in errors if "SLP505" in e[2]]
        assert len(slp505_errors) == 1
        assert "items=[]" in slp505_errors[0][2]

    def test_dict_default_detected(self) -> None:
        code = """
def foo(config={}):
    return config
"""
        errors = check_code(code)
        slp505_errors = [e for e in errors if "SLP505" in e[2]]
        assert len(slp505_errors) == 1
        assert "config={}" in slp505_errors[0][2]

    def test_list_call_default_detected(self) -> None:
        code = """
def foo(items=list()):
    return items
"""
        errors = check_code(code)
        slp505_errors = [e for e in errors if "SLP505" in e[2]]
        assert len(slp505_errors) == 1

    def test_none_default_ok(self) -> None:
        code = """
def foo(items=None):
    if items is None:
        items = []
    return items
"""
        errors = check_code(code)
        slp505_errors = [e for e in errors if "SLP505" in e[2]]
        assert len(slp505_errors) == 0

    def test_tuple_default_ok(self) -> None:
        code = """
def foo(items=(1, 2, 3)):
    return items
"""
        errors = check_code(code)
        slp505_errors = [e for e in errors if "SLP505" in e[2]]
        assert len(slp505_errors) == 0

    def test_ignored_with_noqa(self) -> None:
        code = """
def foo(items=[]):  # noqa: SLP505
    return items
"""
        errors = check_code(code)
        slp505_errors = [e for e in errors if "SLP505" in e[2]]
        assert len(slp505_errors) == 0


class TestFStringNoPlaceholders:
    """Tests for SLP506 - f-string with no placeholders."""

    def test_fstring_no_placeholder_detected(self) -> None:
        code = """
x = f"hello world"
"""
        errors = check_code(code)
        slp506_errors = [e for e in errors if "SLP506" in e[2]]
        assert len(slp506_errors) == 1

    def test_fstring_with_placeholder_ok(self) -> None:
        code = """
name = "world"
x = f"hello {name}"
"""
        errors = check_code(code)
        slp506_errors = [e for e in errors if "SLP506" in e[2]]
        assert len(slp506_errors) == 0

    def test_regular_string_ok(self) -> None:
        code = """
x = "hello world"
"""
        errors = check_code(code)
        slp506_errors = [e for e in errors if "SLP506" in e[2]]
        assert len(slp506_errors) == 0

    def test_ignored_with_noqa(self) -> None:
        code = """
x = f"hello"  # noqa: SLP506
"""
        errors = check_code(code)
        slp506_errors = [e for e in errors if "SLP506" in e[2]]
        assert len(slp506_errors) == 0


class TestRedundantWrapping:
    """Tests for SLP507 - Redundant list/dict/set wrapping."""

    def test_list_empty_detected(self) -> None:
        code = """
x = list()
"""
        errors = check_code(code)
        slp507_errors = [e for e in errors if "SLP507" in e[2]]
        assert len(slp507_errors) == 1

    def test_list_with_list_literal_detected(self) -> None:
        code = """
x = list([1, 2, 3])
"""
        errors = check_code(code)
        slp507_errors = [e for e in errors if "SLP507" in e[2]]
        assert len(slp507_errors) == 1

    def test_dict_empty_detected(self) -> None:
        code = """
x = dict()
"""
        errors = check_code(code)
        slp507_errors = [e for e in errors if "SLP507" in e[2]]
        assert len(slp507_errors) == 1

    def test_dict_with_dict_literal_detected(self) -> None:
        code = """
x = dict({"a": 1})
"""
        errors = check_code(code)
        slp507_errors = [e for e in errors if "SLP507" in e[2]]
        assert len(slp507_errors) == 1

    def test_list_with_generator_ok(self) -> None:
        code = """
x = list(range(10))
"""
        errors = check_code(code)
        slp507_errors = [e for e in errors if "SLP507" in e[2]]
        assert len(slp507_errors) == 0

    def test_dict_with_kwargs_ok(self) -> None:
        code = """
x = dict(a=1, b=2)
"""
        errors = check_code(code)
        slp507_errors = [e for e in errors if "SLP507" in e[2]]
        assert len(slp507_errors) == 0

    def test_ignored_with_noqa(self) -> None:
        code = """
x = list()  # noqa: SLP507
"""
        errors = check_code(code)
        slp507_errors = [e for e in errors if "SLP507" in e[2]]
        assert len(slp507_errors) == 0


class TestUnnecessaryKeys:
    """Tests for SLP508 - Unnecessary .keys() in iteration."""

    def test_for_keys_detected(self) -> None:
        code = """
for k in d.keys():
    print(k)
"""
        errors = check_code(code)
        slp508_errors = [e for e in errors if "SLP508" in e[2]]
        assert len(slp508_errors) == 1

    def test_for_dict_ok(self) -> None:
        code = """
for k in d:
    print(k)
"""
        errors = check_code(code)
        slp508_errors = [e for e in errors if "SLP508" in e[2]]
        assert len(slp508_errors) == 0

    def test_for_items_ok(self) -> None:
        code = """
for k, v in d.items():
    print(k, v)
"""
        errors = check_code(code)
        slp508_errors = [e for e in errors if "SLP508" in e[2]]
        assert len(slp508_errors) == 0

    def test_keys_outside_for_ok(self) -> None:
        code = """
keys = d.keys()
"""
        errors = check_code(code)
        slp508_errors = [e for e in errors if "SLP508" in e[2]]
        assert len(slp508_errors) == 0

    def test_ignored_with_noqa(self) -> None:
        code = """
for k in d.keys():  # noqa: SLP508
    print(k)
"""
        errors = check_code(code)
        slp508_errors = [e for e in errors if "SLP508" in e[2]]
        assert len(slp508_errors) == 0


class TestExplicitReturnNone:
    """Tests for SLP509 - Explicit return None at end of function."""

    def test_explicit_return_none_detected(self) -> None:
        code = """
def foo():
    print("hello")
    return None
"""
        errors = check_code(code)
        slp509_errors = [e for e in errors if "SLP509" in e[2]]
        assert len(slp509_errors) == 1

    def test_bare_return_detected(self) -> None:
        code = """
def foo():
    print("hello")
    return
"""
        errors = check_code(code)
        slp509_errors = [e for e in errors if "SLP509" in e[2]]
        assert len(slp509_errors) == 1

    def test_return_value_ok(self) -> None:
        code = """
def foo():
    return 42
"""
        errors = check_code(code)
        slp509_errors = [e for e in errors if "SLP509" in e[2]]
        assert len(slp509_errors) == 0

    def test_no_return_ok(self) -> None:
        code = """
def foo():
    print("hello")
"""
        errors = check_code(code)
        slp509_errors = [e for e in errors if "SLP509" in e[2]]
        assert len(slp509_errors) == 0

    def test_return_none_in_middle_ok(self) -> None:
        code = """
def foo(x):
    if x < 0:
        return None
    return x
"""
        errors = check_code(code)
        slp509_errors = [e for e in errors if "SLP509" in e[2]]
        assert len(slp509_errors) == 0

    def test_ignored_with_noqa(self) -> None:
        code = """
def foo():
    return None  # noqa: SLP509
"""
        errors = check_code(code)
        slp509_errors = [e for e in errors if "SLP509" in e[2]]
        assert len(slp509_errors) == 0


class TestTypeComparison:
    """Tests for SLP510 - type(x) == T instead of isinstance."""

    def test_type_eq_detected(self) -> None:
        code = """
if type(x) == int:
    pass
"""
        errors = check_code(code)
        slp510_errors = [e for e in errors if "SLP510" in e[2]]
        assert len(slp510_errors) == 1
        assert "isinstance" in slp510_errors[0][2]
        assert "int" in slp510_errors[0][2]

    def test_type_is_detected(self) -> None:
        code = """
if type(x) is str:
    pass
"""
        errors = check_code(code)
        slp510_errors = [e for e in errors if "SLP510" in e[2]]
        assert len(slp510_errors) == 1

    def test_isinstance_ok(self) -> None:
        code = """
if isinstance(x, int):
    pass
"""
        errors = check_code(code)
        slp510_errors = [e for e in errors if "SLP510" in e[2]]
        assert len(slp510_errors) == 0

    def test_type_for_exact_match_ok(self) -> None:
        code = """
# Just calling type() is ok
t = type(x)
"""
        errors = check_code(code)
        slp510_errors = [e for e in errors if "SLP510" in e[2]]
        assert len(slp510_errors) == 0

    def test_ignored_with_noqa(self) -> None:
        code = """
if type(x) == int:  # noqa: SLP510
    pass
"""
        errors = check_code(code)
        slp510_errors = [e for e in errors if "SLP510" in e[2]]
        assert len(slp510_errors) == 0
