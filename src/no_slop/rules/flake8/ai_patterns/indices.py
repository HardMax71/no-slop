from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import cast

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - py310
    import tomli as tomllib

from .constants import TYPE_ALIASES, TYPE_METHOD_SOURCES


@dataclass(frozen=True)
class ModuleIndex:
    stdlib: set[str]
    local: set[str]
    declared: set[str]

    def is_known(self, module: str) -> bool:
        root = module.split(".", 1)[0].lower()
        return root in self.stdlib or root in self.local or root in self.declared


@dataclass(frozen=True)
class TypeIndex:
    attrs: dict[str, set[str]]
    aliases: dict[str, str]

    def resolve(self, name: str) -> str | None:
        key = self.aliases.get(name, name)
        if key in self.attrs:
            return key
        return None

    def has_attr(self, name: str, attr: str) -> bool:
        key = self.resolve(name)
        if key is None:
            return False
        return attr in self.attrs[key]


@lru_cache(maxsize=1)
def _module_index() -> ModuleIndex:
    project_root = Path.cwd()
    return ModuleIndex(
        stdlib=_stdlib_modules(),
        local=_local_modules(project_root),
        declared=_declared_modules(project_root),
    )


@lru_cache(maxsize=1)
def _type_index() -> TypeIndex:
    attrs: dict[str, set[str]] = {}
    typeshed = _typeshed_dir()
    if typeshed is not None:
        for filename, class_names in TYPE_METHOD_SOURCES.items():
            attrs.update(_parse_stub_methods(typeshed / filename, class_names))
    return TypeIndex(attrs=attrs, aliases=TYPE_ALIASES)


def _typeshed_dir() -> Path | None:
    try:
        import mypy
    except ImportError:
        return None
    root = Path(mypy.__file__).resolve().parent
    typeshed = root / "typeshed" / "stdlib"
    return typeshed if typeshed.exists() else None


def _parse_stub_methods(path: Path, class_names: set[str]) -> dict[str, set[str]]:
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    module = ast.parse(text)
    methods: dict[str, set[str]] = {name: set() for name in class_names}
    for node in module.body:
        match node:
            case ast.ClassDef(name=name, body=body) if name in class_names:
                for item in body:
                    match item:
                        case ast.FunctionDef(name=func_name):
                            methods[name].add(func_name)
    return {name: values for name, values in methods.items() if values}


def _stdlib_modules() -> set[str]:
    stdlib = set(sys.builtin_module_names)
    stdlib.update(getattr(sys, "stdlib_module_names", set()))
    return {name.lower() for name in stdlib}


def _local_modules(project_root: Path) -> set[str]:
    modules: set[str] = set()
    skip_dirs = {
        ".git",
        ".venv",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "dist",
    }
    for root in (project_root / "src", project_root):
        if not root.exists():
            continue
        for entry in root.iterdir():
            if entry.name.startswith(".") or entry.name in skip_dirs:
                continue
            if entry.is_dir():
                if (entry / "__init__.py").exists():
                    modules.add(entry.name.lower())
            elif entry.is_file() and entry.suffix == ".py":
                modules.add(entry.stem.lower())
    return modules


def _declared_modules(project_root: Path) -> set[str]:
    pyproject = project_root / "pyproject.toml"
    if not pyproject.exists():
        return set()
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = cast(dict[str, object], data.get("project", {}))
    deps = list(cast(list[str], project.get("dependencies", [])))
    optional = cast(dict[str, list[str]], project.get("optional-dependencies", {}))
    for group in optional.values():
        deps.extend(group)
    modules: set[str] = set()
    for dep in deps:
        name = _dependency_name(dep)
        if name:
            modules.add(_normalize_module_name(name))
    return modules


def _dependency_name(requirement: str) -> str | None:
    try:
        req = Requirement(requirement)
    except InvalidRequirement:
        return None
    return req.name


def _normalize_module_name(name: str) -> str:
    return canonicalize_name(name).replace("-", "_")
