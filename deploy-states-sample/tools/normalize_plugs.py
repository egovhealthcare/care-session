#!/usr/bin/env python3
"""Canonicalize ADDITIONAL_PLUGS in every env/*/build/care/care.env.

Each care.env must store ADDITIONAL_PLUGS as a single heredoc block:

    ADDITIONAL_PLUGS=<<-EOT
    [
      {"name":"<plugin>","version":"@<branch/tag>","package_name":"git+https://github.com/<org>/<repo>.git","configs":{}},
      ...
    ]
    EOT

Semantic rules enforced (not just formatting):
  - ADDITIONAL_PLUGS parses as a JSON array
  - each entry has exactly the keys name, version, package_name, configs
  - configs is always present (empty object when unset)
  - version starts with "@"
  - package_name matches git+https://github.com/<org>/<repo>.git
  - config values are JSON strings, JSON booleans, or arrays of JSON strings
  - no duplicate plugin name within one environment
  - no unterminated heredoc blocks, no lines that are not KEY=VALUE

Usage:
  python3 tools/normalize_plugs.py                    # rewrite files in place (default)
  python3 tools/normalize_plugs.py --apply            # same
  python3 tools/normalize_plugs.py --check            # fail (exit 1) if any file deviates
  python3 tools/normalize_plugs.py --emit FILE        # print resolved KEY=VALUE build-arg lines

In apply mode the script exits 1 when it changed any file (the pre-commit
contract for fixers); it exits 0 when everything is already canonical.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

KEY_VALUE_RE = re.compile(r"^([A-Za-z0-9_]+)=(.*)$")
HEREDOC_RE = re.compile(r"^([A-Za-z0-9_]+)=<<-([A-Za-z0-9_]+)\s*$")

REQUIRED_KEYS = ("name", "version", "package_name")
OPTIONAL_KEYS = ("configs",)
ALL_KEYS = REQUIRED_KEYS + OPTIONAL_KEYS

VERSION_RE = re.compile(r"^@.+")
PACKAGE_RE = re.compile(r"^git\+https://github\.com/[^/\s]+/[^/\s]+\.git$")


class FormatError(Exception):
    pass


def parse_file(text: str):
    items = []
    lines = text.split("\n")
    if lines and lines[-1] == "" and text.endswith("\n"):
        lines.pop()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.startswith("#"):
            items.append(("literal", line))
            i += 1
            continue
        m = HEREDOC_RE.match(line)
        if m:
            key, delim = m.group(1), m.group(2)
            delim_re = re.compile(r"^\s*" + re.escape(delim) + r"\s*$")
            i += 1
            content = []
            while i < len(lines) and not delim_re.match(lines[i]):
                content.append(lines[i])
                i += 1
            if i >= len(lines):
                raise FormatError(
                    f"{key}=<<-{delim} block is not terminated (missing '{delim}')"
                )
            i += 1
            items.append(("heredoc", key, delim, content))
            continue
        m = KEY_VALUE_RE.match(line)
        if m:
            items.append(("kv", m.group(1), m.group(2)))
            i += 1
            continue
        raise FormatError(f"invalid line (expected KEY=VALUE): {line!r}")
    return items


def serialize(items, trailing_newline: bool) -> str:
    out = []
    for it in items:
        kind = it[0]
        if kind == "literal":
            out.append(it[1])
        elif kind == "kv":
            out.append(f"{it[1]}={it[2]}")
        else:
            _, key, delim, content = it
            out.append(f"{key}=<<-{delim}")
            out.extend(content)
            out.append(delim)
    text = "\n".join(out)
    if trailing_newline:
        text += "\n"
    return text


def validate_plugins(plugins, path: str):
    errors = []
    if not isinstance(plugins, list):
        return [f"{path}: ADDITIONAL_PLUGS is not a JSON array"]
    seen = set()
    for i, p in enumerate(plugins):
        if not isinstance(p, dict):
            errors.append(f"{path}: plugin entry {i} is not a JSON object")
            continue
        label = p.get("name") if isinstance(p.get("name"), str) else f"<entry {i}>"
        # Require string types for identity fields
        for field in ("name", "version", "package_name"):
            if field in p and not isinstance(p[field], str):
                errors.append(
                    f"{path}: {label}: {field} must be a string, "
                    f"got {type(p[field]).__name__}"
                )
        missing = [k for k in REQUIRED_KEYS if k not in p]
        unknown = [k for k in p if k not in ALL_KEYS]
        if missing:
            errors.append(f"{path}: {label}: missing keys: {', '.join(missing)}")
        if unknown:
            errors.append(f"{path}: {label}: unknown keys: {', '.join(unknown)}")
        if "version" in p and not VERSION_RE.match(str(p["version"])):
            errors.append(
                f"{path}: {label}: version must start with '@', got {p['version']!r}"
            )
        if "package_name" in p and not PACKAGE_RE.match(str(p["package_name"])):
            errors.append(
                f"{path}: {label}: package_name must be "
                f"'git+https://github.com/<org>/<repo>.git', got {p['package_name']!r}"
            )
        if "configs" in p:
            cfg = p["configs"]
            if not isinstance(cfg, dict):
                errors.append(f"{path}: {label}: configs must be a JSON object")
            else:
                for k, v in cfg.items():
                    is_string_array = isinstance(v, list) and all(
                        isinstance(item, str) for item in v
                    )
                    if (
                        not isinstance(v, str)
                        and not isinstance(v, bool)
                        and not is_string_array
                    ):
                        errors.append(
                            f"{path}: {label}: configs.{k} must be a JSON string, "
                            f"JSON boolean, or an array of JSON strings, "
                            f"got {type(v).__name__}"
                        )
        name = p.get("name")
        if isinstance(name, str):
            if name in seen:
                errors.append(f"{path}: duplicate plugin name {name!r}")
            seen.add(name)
    return errors


def canonical_plugins(plugins):
    out = []
    for p in plugins:
        out.append(
            {
                "name": p["name"],
                "version": p["version"],
                "package_name": p["package_name"],
                "configs": canonical_configs(p.get("configs", {})),
            }
        )
    return out


def canonical_configs(configs):
    return {
        key: canonical_config_value(value)
        for key, value in configs.items()
    }


def canonical_config_value(value):
    if value == "True":
        return True
    if value == "False":
        return False
    return value


def plugin_lines(plugins):
    lines = ["["]
    for i, p in enumerate(plugins):
        sep = "," if i < len(plugins) - 1 else ""
        lines.append("  " + json.dumps(p, separators=(",", ":")) + sep)
    lines.append("]")
    return lines


def normalize_items(items, path: str, *, require_plugs: bool = True):
    errors = []
    out = []
    plug_count = 0
    for it in items:
        if it[0] in ("kv", "heredoc") and it[1] == "ADDITIONAL_PLUGS":
            plug_count += 1
            value = it[2] if it[0] == "kv" else "\n".join(it[3])
            try:
                plugins = json.loads(value)
            except json.JSONDecodeError as exc:
                errors.append(f"{path}: ADDITIONAL_PLUGS is not valid JSON: {exc}")
                out.append(it)
                continue
            errs = validate_plugins(plugins, path)
            if errs:
                errors.extend(errs)
                out.append(it)
                continue
            out.append(
                ("heredoc", "ADDITIONAL_PLUGS", "EOT", plugin_lines(canonical_plugins(plugins)))
            )
        else:
            out.append(it)
    if require_plugs and plug_count == 0:
        errors.append(f"{path}: missing ADDITIONAL_PLUGS declaration")
    elif plug_count > 1:
        errors.append(f"{path}: multiple ADDITIONAL_PLUGS declarations (found {plug_count})")
    return out, errors


def emit_lines(items):
    out = []
    for it in items:
        kind = it[0]
        if kind == "literal":
            continue
        if kind == "kv":
            out.append(f"{it[1]}={it[2]}")
        else:
            _, key, _, content = it
            if key == "ADDITIONAL_PLUGS":
                # JSON can be safely space-joined
                parts = [c.strip() for c in content if c.strip()]
                out.append(f"{key}={' '.join(parts)}")
            else:
                # Preserve newlines for non-JSON heredocs
                out.append(f"{key}={''.join(c + chr(10) for c in content).rstrip(chr(10))}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Normalize ADDITIONAL_PLUGS in env/*/build/care/care.env"
    )
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true", help="rewrite files in place (default)")
    group.add_argument("--check", action="store_true", help="fail if any file is not canonical")
    group.add_argument("--emit", metavar="ENV_FILE", help="print resolved KEY=VALUE build-arg lines")
    args = ap.parse_args()

    if args.emit:
        path = ROOT / args.emit
        if not path.is_file():
            print(f"error: no such file: {path}", file=sys.stderr)
            return 1
        try:
            items = parse_file(path.read_text())
        except FormatError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        # Validate ADDITIONAL_PLUGS if present, but don't require it
        # (care_fe.env and other component env files won't have it)
        items, errs = normalize_items(items, str(path), require_plugs=False)
        if errs:
            print("ERRORS:", file=sys.stderr)
            for e in errs:
                print("  " + e, file=sys.stderr)
            return 1
        for line in emit_lines(items):
            print(line)
        return 0

    apply = args.apply or not args.check

    paths = sorted(ROOT.glob("env/*/build/care/care.env"))
    if not paths:
        print("error: no care.env files found", file=sys.stderr)
        return 1

    parsed = []
    all_errors = []
    for path in paths:
        text = path.read_text()
        try:
            items = parse_file(text)
        except FormatError as exc:
            all_errors.append(f"{path}: {exc}")
            continue
        items, errs = normalize_items(items, str(path))
        all_errors.extend(errs)
        parsed.append((path, items, text.endswith("\n")))

    if all_errors:
        print("ERRORS:", file=sys.stderr)
        for e in all_errors:
            print("  " + e, file=sys.stderr)
        return 1

    changed = []
    for path, items, trailing in parsed:
        new_text = serialize(items, trailing)
        if new_text != path.read_text():
            changed.append((path, new_text))

    if args.check:
        for path, _ in changed:
            print(f"{path}: NOT canonical (run: python3 tools/normalize_plugs.py)")
        if changed:
            return 1
        print("OK: all care.env files are canonical")
        return 0

    for path, new_text in changed:
        path.write_text(new_text)
        print(f"normalized {path}")
    if not changed:
        print("OK: already canonical")
        return 0
    print("Files changed — stage them and commit again.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
