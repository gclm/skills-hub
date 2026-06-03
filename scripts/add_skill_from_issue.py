#!/usr/bin/env python3
"""Add a new skill from a GitHub Issue submission.

Parses the structured Issue body, validates the input, creates the
skill directory (for local skills) or registers the source (for external
skills), and updates hub.yaml.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
HUB_FILE = REPO_ROOT / "hub.yaml"
VALID_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

yaml = YAML()
yaml.preserve_quotes = True
yaml.default_flow_style = False


# ── Issue body parser ──────────────────────────────────────────────


def parse_issue_body(body: str) -> dict[str, str]:
    """Parse GitHub Issue form body into {field_id: value} mapping.

    GitHub issue forms render as:
        ### Label

        value
    """
    fields: dict[str, str] = {}

    # Split on ### headers
    parts = re.split(r"^### (.+)$", body, flags=re.MULTILINE)

    # Map from label to field id
    label_to_id = {
        "Skill 类型": "skill-type",
        "Skill ID": "skill-id",
        "描述": "description",
        "上游仓库 URL（仅 External）": "repo-url",
        "分支/标签（仅 External）": "ref",
        "子目录路径（可选，仅 External）": "subpath",
        "许可证（可选）": "license",
        "作者（可选）": "author",
        "SKILL.md 内容（仅 Local）": "skill-content",
    }

    # parts[0] is before first header, then alternating (label, value)
    for i in range(1, len(parts) - 1, 2):
        label = parts[i].strip()
        value = parts[i + 1].strip() if i + 1 < len(parts) else ""
        field_id = label_to_id.get(label)
        if field_id:
            fields[field_id] = value

    # Handle "No response" → treat as empty
    for k in fields:
        if fields[k] == "_No response_":
            fields[k] = ""

    return fields


# ── Validation ─────────────────────────────────────────────────────


def load_hub() -> dict:
    """Load hub.yaml."""
    with open(HUB_FILE) as f:
        return yaml.load(f)


def save_hub(hub: dict) -> None:
    """Save hub.yaml preserving formatting."""
    with open(HUB_FILE, "w") as f:
        yaml.dump(hub, f)


def validate_fields(fields: dict, hub: dict) -> list[str]:
    """Validate parsed fields. Returns error list."""
    errors: list[str] = []

    # skill-id
    sid = fields.get("skill-id", "").strip()
    if not sid:
        errors.append("Skill ID is required")
    elif not VALID_ID_RE.match(sid):
        errors.append(f"Skill ID '{sid}' must be kebab-case (lowercase, digits, hyphens)")

    # Check uniqueness
    existing_ids = {s["id"] for s in hub.get("skills", []) if isinstance(s, dict)}
    if sid in existing_ids:
        errors.append(f"Skill ID '{sid}' already exists in hub.yaml")

    # skill-type
    stype_raw = fields.get("skill-type", "").strip()
    if "local" in stype_raw.lower():
        stype = "local"
    elif "external" in stype_raw.lower():
        stype = "external"
    else:
        errors.append("Skill type must be Local or External")
        stype = ""

    # description
    desc = fields.get("description", "").strip()
    if not desc:
        errors.append("Description is required")

    # type-specific validation
    if stype == "external":
        repo_url = fields.get("repo-url", "").strip()
        ref = fields.get("ref", "").strip()
        if not repo_url:
            errors.append("Upstream repo URL is required for External skills")
        if not ref:
            errors.append("Branch/tag is required for External skills")

    if stype == "local":
        content = fields.get("skill-content", "").strip()
        if not content:
            errors.append("SKILL.md content is required for Local skills")

    return errors


# ── Skill creation ─────────────────────────────────────────────────


def add_local_skill(sid: str, desc: str, content: str, hub: dict,
                    metadata: dict) -> None:
    """Create a local skill directory with SKILL.md and register in hub."""
    skill_dir = REPO_ROOT / sid
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Write SKILL.md
    (skill_dir / "SKILL.md").write_text(content + "\n")

    # Register in hub.yaml
    entry = {
        "id": sid,
        "type": "local",
        "path": sid,
        "description": desc,
    }
    if metadata.get("license"):
        entry["metadata"] = {"license": metadata["license"]}
        if metadata.get("author"):
            entry["metadata"]["author"] = metadata["author"]

    hub["skills"].append(entry)
    save_hub(hub)


def add_external_skill(sid: str, desc: str, repo_url: str, ref: str,
                       subpath: str, hub: dict, metadata: dict) -> None:
    """Register an external skill in hub.yaml."""
    entry = {
        "id": sid,
        "type": "external",
        "path": sid,
        "description": desc,
        "source": {
            "repo": repo_url,
            "ref": ref,
        },
        "last_synced": {
            "commit_sha": "",
            "synced_at": "",
        },
    }

    if subpath:
        entry["source"]["subpath"] = subpath

    if metadata.get("license") or metadata.get("author"):
        entry["metadata"] = {}
        if metadata.get("license"):
            entry["metadata"]["license"] = metadata["license"]
        if metadata.get("author"):
            entry["metadata"]["author"] = metadata["author"]

    hub["skills"].append(entry)
    save_hub(hub)


# ── Main ───────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Add skill from Issue")
    parser.add_argument("--issue-body", type=Path, required=True,
                        help="File containing issue body")
    parser.add_argument("--issue-number", type=int, required=True,
                        help="Issue number")
    parser.add_argument("--output", type=Path,
                        default=REPO_ROOT / "_add_result.json",
                        help="Path for result JSON")
    args = parser.parse_args()

    # Parse issue body
    body = args.issue_body.read_text()
    fields = parse_issue_body(body)

    print("Parsed fields:")
    for k, v in fields.items():
        display_v = v[:80] + "..." if len(v) > 80 else v
        print(f"  {k}: {display_v}")

    # Load hub
    hub = load_hub()

    # Validate
    errors = validate_fields(fields, hub)
    if errors:
        print(f"\n❌ Validation failed ({len(errors)} error(s)):")
        for e in errors:
            print(f"  • {e}")
        # Write error result
        args.output.write_text(json.dumps({
            "success": False,
            "errors": errors,
        }, indent=2, ensure_ascii=False))
        return 1

    # Extract fields
    sid = fields["skill-id"].strip()
    desc = fields["description"].strip()
    stype_raw = fields["skill-type"].strip()
    stype = "local" if "local" in stype_raw.lower() else "external"

    metadata = {
        "license": fields.get("license", "").strip(),
        "author": fields.get("author", "").strip(),
    }

    if stype == "local":
        content = fields["skill-content"].strip()
        add_local_skill(sid, desc, content, hub, metadata)
        print(f"\n✅ Local skill '{sid}' created at {sid}/SKILL.md")
    else:
        repo_url = fields["repo-url"].strip()
        ref = fields.get("ref", "main").strip() or "main"
        subpath = fields.get("subpath", "").strip()
        add_external_skill(sid, desc, repo_url, ref, subpath, hub, metadata)
        print(f"\n✅ External skill '{sid}' registered (will sync on next workflow run)")

    # Write success result
    result = {
        "success": True,
        "skill_id": sid,
        "type": stype,
        "issue_number": args.issue_number,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
