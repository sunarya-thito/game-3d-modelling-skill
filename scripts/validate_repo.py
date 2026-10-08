#!/usr/bin/env python3
"""Validate an Agent Skill repository with no third-party dependencies."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


TEXT_SUFFIXES = {
    ".md", ".txt", ".py", ".json", ".yaml", ".yml", ".toml", ".ini",
    ".cfg", ".sh", ".ps1", ".bat", ".js", ".ts", ".html", ".css",
}
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "build", "dist"}
PLACEHOLDER_PATTERNS = (
    re.compile(r"\bTODO\b", re.IGNORECASE),
    re.compile(r"\bFIXME\b", re.IGNORECASE),
    re.compile(r"\bCHANGEME\b", re.IGNORECASE),
)
LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\((?!https?://|mailto:|#)([^)]+)\)")
FRONTMATTER_PATTERN = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
NAME_PATTERN = re.compile(r"^(?!-)(?!.*--)[a-z0-9-]{1,64}(?<!-)$")


def iter_text_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in {"LICENSE", "Makefile"}:
            yield path


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def validate_frontmatter(
    skill: Path,
    errors: list[str],
    require_parent_name: bool = True,
) -> None:
    text = skill.read_text(encoding="utf-8")
    match = FRONTMATTER_PATTERN.match(text)
    if not match:
        errors.append("SKILL.md: missing YAML frontmatter")
        return
    fields = {}
    for line in match.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    name = fields.get("name", "")
    description = fields.get("description", "")
    if not NAME_PATTERN.fullmatch(name):
        errors.append(
            "SKILL.md: name must be 1-64 lowercase letters, digits, or single internal hyphens"
        )
    if require_parent_name and name and name != skill.parent.name:
        errors.append(
            f"SKILL.md: name {name!r} must match parent directory {skill.parent.name!r}"
        )
    if not description or len(description) > 1024:
        errors.append("SKILL.md: description must contain 1-1024 characters")
    if len(text.splitlines()) > 500:
        errors.append("SKILL.md: keep the file under 500 lines and move detail to references")


def validate_links(path: Path, root: Path, text: str, errors: list[str]) -> None:
    for raw in LINK_PATTERN.findall(text):
        target = raw.strip().split("#", 1)[0].strip("<>")
        if not target:
            continue
        destination = (path.parent / target).resolve()
        try:
            destination.relative_to(root.resolve())
        except ValueError:
            errors.append(f"{relative(path, root)}: local link escapes repository: {raw}")
            continue
        if not destination.exists():
            errors.append(f"{relative(path, root)}: broken local link: {raw}")


def validate_text(path: Path, root: Path, errors: list[str], warnings: list[str]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        errors.append(f"{relative(path, root)}: text file is not valid UTF-8")
        return
    rel = relative(path, root)
    validate_links(path, root, text, errors)
    if path.name == "SKILL.md" and "\\" in text:
        warnings.append(f"{rel}: use forward slashes in skill paths")
    if rel not in {"README.md", "scripts/validate_repo.py", "tests/test_validate_repo.py"}:
        for pattern in PLACEHOLDER_PATTERNS:
            if pattern.search(text):
                warnings.append(f"{rel}: unfinished placeholder keyword found")
                break


def validate_repo(
    root: Path,
    require_parent_name: bool = True,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    skill = root / "SKILL.md"
    if not skill.is_file():
        errors.append("SKILL.md: required file is missing")
    else:
        validate_frontmatter(skill, errors, require_parent_name=require_parent_name)
    for path in iter_text_files(root):
        validate_text(path, root, errors, warnings)
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", type=Path)
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    parser.add_argument(
        "--repository-root",
        action="store_true",
        help="allow the source repository name to differ from the installed skill name",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    errors, warnings = validate_repo(
        root,
        require_parent_name=not args.repository_root,
    )
    for item in warnings:
        print(f"WARNING: {item}")
    for item in errors:
        print(f"ERROR: {item}")
    failed = bool(errors or (args.strict and warnings))
    print(
        f"Validation {'FAILED' if failed else 'PASSED'}: "
        f"{len(errors)} error(s), {len(warnings)} warning(s)"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
