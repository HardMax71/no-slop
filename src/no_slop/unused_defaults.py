from __future__ import annotations

import argparse
import ast
import json
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

__all__ = ["UnusedDefaultsChecker", "main"]


@dataclass
class ParamInfo:
    name: str
    position: int
    default_value: str
    default_line: int
    default_col: int
    is_kwonly: bool = False


@dataclass
class FunctionSignature:
    name: str
    qualified_name: str
    file: str
    line: int
    params: list[ParamInfo]
    params_with_defaults: list[ParamInfo]
    num_required_positional: int
    has_var_positional: bool
    has_var_keyword: bool


@dataclass
class CallSiteInfo:
    file: str
    line: int
    col: int
    callee_name: str
    num_positional_args: int
    keyword_arg_names: set[str]
    has_star_args: bool
    has_star_kwargs: bool


@dataclass
class UnusedDefaultIssue:
    file: str
    line: int
    col: int
    function_name: str
    param_name: str
    default_value: str
    num_call_sites: int
    message: str


class SignatureExtractor(ast.NodeVisitor):
    """Extract function signatures from a file."""

    def __init__(self, file_path: str, module_name: str):
        self.file_path = file_path
        self.module_name = module_name
        self.signatures: list[FunctionSignature] = []
        self._scope_stack: list[str] = []

    def _qualified_name(self, name: str) -> str:
        parts = [self.module_name] + self._scope_stack + [name]
        return ".".join(parts)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._scope_stack.append(node.name)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._extract_signature(node)
        self._scope_stack.append(node.name)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._extract_signature(node)
        self._scope_stack.append(node.name)
        self.generic_visit(node)
        self._scope_stack.pop()

    def _extract_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        args = node.args
        params: list[ParamInfo] = []
        params_with_defaults: list[ParamInfo] = []

        all_args = args.args
        num_defaults = len(args.defaults)
        num_args = len(all_args)
        first_default_idx = num_args - num_defaults

        start_idx = 0
        if self._scope_stack and all_args:
            first_arg = all_args[0].arg
            if first_arg in ("self", "cls"):
                start_idx = 1

        for i, arg in enumerate(all_args[start_idx:], start=start_idx):
            default_idx = i - first_default_idx
            has_default = 0 <= default_idx < len(args.defaults)

            param = ParamInfo(
                name=arg.arg,
                position=i - start_idx,
                default_value=(
                    ""
                    if not has_default
                    else self._repr_default(args.defaults[default_idx])
                ),
                default_line=args.defaults[default_idx].lineno if has_default else 0,
                default_col=args.defaults[default_idx].col_offset if has_default else 0,
                is_kwonly=False,
            )
            params.append(param)
            if has_default:
                params_with_defaults.append(param)

        for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=False):
            if default is None:
                param = ParamInfo(
                    name=arg.arg,
                    position=-1,
                    default_value="",
                    default_line=0,
                    default_col=0,
                    is_kwonly=True,
                )
            else:
                param = ParamInfo(
                    name=arg.arg,
                    position=-1,
                    default_value=self._repr_default(default),
                    default_line=default.lineno,
                    default_col=default.col_offset,
                    is_kwonly=True,
                )
                params_with_defaults.append(param)
            params.append(param)

        if params_with_defaults:
            sig = FunctionSignature(
                name=node.name,
                qualified_name=self._qualified_name(node.name),
                file=self.file_path,
                line=node.lineno,
                params=params,
                params_with_defaults=params_with_defaults,
                num_required_positional=first_default_idx - start_idx,
                has_var_positional=args.vararg is not None,
                has_var_keyword=args.kwarg is not None,
            )
            self.signatures.append(sig)

    def _repr_default(self, node: ast.expr) -> str:
        if isinstance(node, ast.Constant):
            return repr(node.value)
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.List):
            return "[...]"
        if isinstance(node, ast.Dict):
            return "{...}"
        if isinstance(node, ast.Set):
            return "{...}"
        if isinstance(node, ast.Tuple):
            return "(...)"
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return f"{node.func.id}()"
            return "<call>"
        if isinstance(node, ast.Lambda):
            return "lambda"
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            inner = self._repr_default(node.operand)
            return f"-{inner}"
        return "<expr>"


class CallSiteExtractor(ast.NodeVisitor):
    """Extract all call sites from a file."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.call_sites: list[CallSiteInfo] = []

    def visit_Call(self, node: ast.Call) -> None:
        callee = self._resolve_callee(node.func)
        if callee:
            keywords = set()
            for kw in node.keywords:
                if kw.arg:
                    keywords.add(kw.arg)

            has_star = any(isinstance(arg, ast.Starred) for arg in node.args)
            has_double_star = any(kw.arg is None for kw in node.keywords)

            self.call_sites.append(
                CallSiteInfo(
                    file=self.file_path,
                    line=node.lineno,
                    col=node.col_offset,
                    callee_name=callee,
                    num_positional_args=len(
                        [a for a in node.args if not isinstance(a, ast.Starred)]
                    ),
                    keyword_arg_names=keywords,
                    has_star_args=has_star,
                    has_star_kwargs=has_double_star,
                )
            )

        self.generic_visit(node)

    def _resolve_callee(self, node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parts: list[str] = []
            current: ast.expr = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
                return ".".join(reversed(parts))
        return None


class UnusedDefaultsChecker:
    """Main analyzer for detecting unused defaults."""

    def __init__(self, project_root: str, quiet: bool = False):
        self.project_root = Path(project_root).resolve()
        self.quiet = quiet
        self.signatures: dict[str, FunctionSignature] = {}
        self.signatures_by_simple_name: dict[str, list[FunctionSignature]] = {}
        self.call_sites: list[CallSiteInfo] = []

    def analyze(self) -> list[UnusedDefaultIssue]:
        """Run the full analysis."""
        if not self.quiet:
            print("Phase 1: Extracting function signatures...")
        self._extract_all_signatures()
        if not self.quiet:
            print(f"  Found {len(self.signatures)} functions with defaults")

        if not self.quiet:
            print("Phase 2: Extracting call sites...")
        self._extract_all_call_sites()
        if not self.quiet:
            print(f"  Found {len(self.call_sites)} call sites")

        if not self.quiet:
            print("Phase 3: Analyzing unused defaults...")
        issues = self._find_unused_defaults()
        if not self.quiet:
            print(f"  Found {len(issues)} unused defaults")

        return issues

    def _iter_python_files(self) -> Iterator[Path]:
        for path in self.project_root.rglob("*.py"):
            parts = path.parts
            skip_dirs = ("__pycache__", "venv", ".venv", "node_modules")
            if any(p.startswith(".") or p in skip_dirs for p in parts):
                continue
            yield path

    def _extract_all_signatures(self) -> None:
        for path in self._iter_python_files():
            try:
                source = path.read_text()
                tree = ast.parse(source, filename=str(path))
            except (SyntaxError, UnicodeDecodeError):
                continue

            rel_path = str(path.relative_to(self.project_root))
            module_name = (
                rel_path.replace("/", ".").replace("\\", ".").removesuffix(".py")
            )

            extractor = SignatureExtractor(rel_path, module_name)
            extractor.visit(tree)

            for sig in extractor.signatures:
                self.signatures[sig.qualified_name] = sig

                if sig.name not in self.signatures_by_simple_name:
                    self.signatures_by_simple_name[sig.name] = []
                self.signatures_by_simple_name[sig.name].append(sig)

    def _extract_all_call_sites(self) -> None:
        for path in self._iter_python_files():
            try:
                source = path.read_text()
                tree = ast.parse(source, filename=str(path))
            except (SyntaxError, UnicodeDecodeError):
                continue

            rel_path = str(path.relative_to(self.project_root))
            extractor = CallSiteExtractor(rel_path)
            extractor.visit(tree)
            self.call_sites.extend(extractor.call_sites)

    def _find_unused_defaults(self) -> list[UnusedDefaultIssue]:
        issues = []

        calls_by_name: dict[str, list[CallSiteInfo]] = {}
        for call in self.call_sites:
            name = call.callee_name
            if name not in calls_by_name:
                calls_by_name[name] = []
            calls_by_name[name].append(call)

            if "." in name:
                short_name = name.split(".")[-1]
                if short_name not in calls_by_name:
                    calls_by_name[short_name] = []
                calls_by_name[short_name].append(call)

        for _qualified_name, sig in self.signatures.items():
            if sig.name.startswith("_") and not sig.name.startswith("__"):
                continue

            candidate_calls = calls_by_name.get(sig.name, [])

            for variant in self._name_variants(sig):
                if variant in calls_by_name:
                    candidate_calls.extend(calls_by_name[variant])

            seen = set()
            unique_calls = []
            for call in candidate_calls:
                key = (call.file, call.line, call.col)
                if key not in seen:
                    seen.add(key)
                    unique_calls.append(call)

            if not unique_calls:
                continue

            for param in sig.params_with_defaults:
                unused = self._is_param_default_unused(sig, param, unique_calls)
                if unused:
                    issues.append(
                        UnusedDefaultIssue(
                            file=sig.file,
                            line=param.default_line,
                            col=param.default_col,
                            function_name=sig.name,
                            param_name=param.name,
                            default_value=param.default_value,
                            num_call_sites=len(unique_calls),
                            message=f"Default '{param.default_value}' for '{param.name}' "
                            f"is never used ({len(unique_calls)} call sites)",
                        )
                    )

        return issues

    def _name_variants(self, sig: FunctionSignature) -> list[str]:
        """Generate possible name variants for matching."""
        variants = [sig.name, sig.qualified_name]

        parts = sig.qualified_name.split(".")
        if len(parts) >= 2:
            variants.append(f"{parts[-2]}.{parts[-1]}")

        return variants

    def _is_param_default_unused(
        self,
        sig: FunctionSignature,
        param: ParamInfo,
        calls: list[CallSiteInfo],
    ) -> bool:
        """Check if a parameter's default is never used across all call sites."""
        for call in calls:
            if call.has_star_args or call.has_star_kwargs:
                return False

            if param.is_kwonly:
                if param.name not in call.keyword_arg_names:
                    return False
            else:
                provided_positionally = call.num_positional_args > param.position
                provided_as_keyword = param.name in call.keyword_arg_names

                if not provided_positionally and not provided_as_keyword:
                    return False

        return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect unused default parameter values (SLP010)"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to analyze (default: current directory)",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--min-calls",
        type=int,
        default=1,
        help="Minimum call sites to report (default: 1)",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress progress output"
    )

    args = parser.parse_args()

    checker = UnusedDefaultsChecker(args.path, quiet=args.quiet or args.json)
    issues = checker.analyze()

    issues = [i for i in issues if i.num_call_sites >= args.min_calls]

    if args.json:
        output = [
            {
                "code": "SLP010",
                "file": issue.file,
                "line": issue.line,
                "col": issue.col,
                "function": issue.function_name,
                "param": issue.param_name,
                "default": issue.default_value,
                "call_sites": issue.num_call_sites,
                "message": issue.message,
            }
            for issue in issues
        ]
        print(json.dumps(output, indent=2))
    else:
        print(f"\nFound {len(issues)} unused defaults:\n")

        for issue in sorted(issues, key=lambda i: (i.file, i.line)):
            print(f"{issue.file}:{issue.line}:{issue.col}: SLP010")
            print(f"  Function: {issue.function_name}")
            print(f"  Parameter: {issue.param_name} = {issue.default_value}")
            print(f"  {issue.message}\n")

    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
