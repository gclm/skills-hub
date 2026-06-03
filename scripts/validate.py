#!/usr/bin/env python3
"""Validate hub.yaml schema and SKILL.md frontmatter."""

import argparse
import os
import re
import sys
from pathlib import Path

import yaml

# ── Constants ──────────────────────────────────────────────────────

VALID_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
VALID_TYPES = ("local", "external")
REQUIRED_FRONTMATTER = ("name", "description")

REPO_ROOT = Path(__file__).resolve().parent.parent


# ── hub.yaml validation ───────────────────────────────────────────


def validate_hub(hub_path: Path) -> list[str]:
    """Validate hub.yaml schema. Returns list of error messages."""
    errors: list[str] = []

    if not hub_path.exists():
        return [f"hub.yaml not found at {hub_path}"]

    with open(hub_path) as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            return [f"hub.yaml parse error: {e}"]

    # Top-level fields
    if not isinstance(data, dict):
        return ["hub.yaml root must be a mapping"]

    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    skills = data.get("skills")
    if not isinstance(skills, list) or len(skills) == 0:
        errors.append("skills must be a non-empty list")
        return errors

    # Check for duplicate ids and paths
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()

    for i, skill in enumerate(skills, 1):
        prefix = f"skills[{i}]"

        if not isinstance(skill, dict):
            errors.append(f"{prefix}: must be a mapping")
            continue

        # id
        sid = skill.get("id")
        if not sid:
            errors.append(f"{prefix}: 'id' is required")
        elif not VALID_ID_RE.match(str(sid)):
            errors.append(f"{prefix}: id '{sid}' must match {VALID_ID_RE.pattern}")
        elif sid in seen_ids:
            errors.append(f"{prefix}: duplicate id '{sid}'")
        else:
            seen_ids.add(str(sid))

        # type
        stype = skill.get("type")
        if stype not in VALID_TYPES:
            errors.append(f"{prefix}: type must be one of {VALID_TYPES}, got '{stype}'")

        # path
        spath = skill.get("path")
        if not spath:
            errors.append(f"{prefix}: 'path' is required")
        else:
            spath = str(spath)
            if spath in seen_paths:
                errors.append(f"{prefix}: duplicate path '{spath}'")
            else:
                seen_paths.add(spath)
            skill_dir = REPO_ROOT / spath
            if not skill_dir.is_dir():
                errors.append(f"{prefix}: path '{spath}' does not exist")

        # description
        desc = skill.get("description")
        if not desc or not str(desc).strip():
            errors.append(f"{prefix}: 'description' is required and non-empty")

        # external-specific
        if stype == "external":
            source = skill.get("source", {})
            if not isinstance(source, dict):
                errors.append(f"{prefix}: 'source' must be a mapping for external skills")
            else:
                if not source.get("repo"):
                    errors.append(f"{prefix}: source.repo is required for external skills")
                if not source.get("ref"):
                    errors.append(f"{prefix}: source.ref is required for external skills")

    return errors


# ── SKILL.md validation ───────────────────────────────────────────


def parse_frontmatter(text: str) -> dict | None:
    """Extract YAML frontmatter from SKILL.md content."""
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        return yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None


def validate_skill_md(hub_path: Path) -> list[str]:
    """Validate all SKILL.md files and cross-reference with hub.yaml."""
    errors: list[str] = []

    # Find all SKILL.md files
    skill_dirs: dict[str, Path] = {}
    for entry in sorted(REPO_ROOT.iterdir()):
        skill_file = entry / "SKILL.md"
        if entry.is_dir() and skill_file.exists():
            skill_dirs[entry.name] = skill_file

    # Load hub paths for cross-reference
    hub_paths: set[str] = set()
    if hub_path.exists():
        with open(hub_path) as f:
            data = yaml.safe_load(f) or {}
        for skill in data.get("skills", []):
            if isinstance(skill, dict) and skill.get("path"):
                hub_paths.add(str(skill["path"]))

    # Check each SKILL.md
    for dir_name, skill_file in skill_dirs.items():
        with open(skill_file) as f:
            content = f.read()

        fm = parse_frontmatter(content)
        if fm is None:
            errors.append(f"{dir_name}/SKILL.md: missing or invalid YAML frontmatter")
            continue

        for field in REQUIRED_FRONTMATTER:
            val = fm.get(field)
            if not val or not str(val).strip():
                errors.append(f"{dir_name}/SKILL.md: '{field}' is required in frontmatter")

        # Cross-reference: skill dir must be in hub.yaml
        if dir_name not in hub_paths:
            errors.append(f"{dir_name}/SKILL.md: directory not registered in hub.yaml")

    # Cross-reference: hub paths must have SKILL.md
    for p in hub_paths:
        if p not in skill_dirs:
            errors.append(f"hub.yaml path '{p}': no SKILL.md found")

    return errors


# ── Main ───────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Skills Hub")
    parser.add_argument("--hub-file", type=Path, default=REPO_ROOT / "hub.yaml",
                        help="Path to hub.yaml")
    parser.add_argument("--check-skill-md", action="store_true",
                        help="Also validate SKILL.md files and cross-reference")
    args = parser.parse_args()

    all_errors: list[str] = []

    # 1. Validate hub.yaml
    print("Validating hub.yaml ...")
    hub_errors = validate_hub(args.hub_file)
    all_errors.extend(hub_errors)

    # 2. Validate SKILL.md files (optional)
    if args.check_skill_md:
        print("Validating SKILL.md files ...")
        skill_errors = validate_skill_md(args.hub_file)
        all_errors.extend(skill_errors)

    # Report
    if all_errors:
        print(f"\n❌ Found {len(all_errors)} error(s):\n")
        for err in all_errors:
            print(f"  • {err}")
        return 1

    print("\n✅ All validations passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
