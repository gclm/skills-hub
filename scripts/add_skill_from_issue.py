#!/usr/bin/env python3
"""Add a new skill from a GitHub Issue submission.

Minimal Issue template: only repo URL is required.
The script auto-detects: skill name, description, license, author
by cloning the upstream repo and reading SKILL.md + metadata.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
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


# ── Helpers ────────────────────────────────────────────────────────


def git(*args: str, cwd: Path | None = None, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def parse_issue_body(body: str) -> dict[str, str]:
    """Parse GitHub Issue form body into {field_id: value}."""
    fields: dict[str, str] = {}
    label_to_id = {
        "仓库地址": "repo-url",
        "子目录路径（可选）": "subpath",
        "分支 / 标签（可选）": "ref",
    }
    parts = re.split(r"^### (.+)$", body, flags=re.MULTILINE)
    for i in range(1, len(parts) - 1, 2):
        label = parts[i].strip()
        value = parts[i + 1].strip() if i + 1 < len(parts) else ""
        field_id = label_to_id.get(label)
        if field_id:
            fields[field_id] = "" if value == "_No response_" else value
    return fields


def parse_frontmatter(text: str) -> dict | None:
    """Extract YAML frontmatter from markdown."""
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        import yaml as _yaml
        return _yaml.safe_load(parts[1])
    except Exception:
        return None


def detect_license(repo_dir: Path) -> str:
    """Try to detect license from LICENSE / LICENSE.md."""
    for name in ("LICENSE", "LICENSE.md", "LICENSE.txt"):
        f = repo_dir / name
        if f.exists():
            content = f.read_text(errors="ignore")[:500].lower()
            if "mit" in content:
                return "MIT"
            if "apache" in content:
                return "Apache-2.0"
            if "gpl" in content:
                return "GPL-3.0"
            return "Custom"
    return ""


def detect_author(repo_dir: Path) -> str:
    """Try to detect author from git log or package.json."""
    # Try package.json
    pkg = repo_dir / "package.json"
    if pkg.exists():
        try:
            import json as _json
            data = _json.loads(pkg.read_text())
            if data.get("author"):
                return str(data["author"])
        except Exception:
            pass
    # Try git log
    try:
        name = git("log", "-1", "--format=%aN", cwd=repo_dir)
        if name:
            return name
    except Exception:
        pass
    return ""


# ── Core logic ─────────────────────────────────────────────────────


def add_skill(fields: dict, hub: dict) -> dict:
    """Clone upstream, detect metadata, create skill, update hub.yaml.
    Returns result dict with success/error info."""
    repo_url = fields.get("repo-url", "").strip()
    if not repo_url:
        return {"success": False, "errors": ["仓库地址是必填项"]}

    # Normalize URL (accept both with/without .git)
    if not repo_url.startswith("http") and not repo_url.startswith("git@"):
        repo_url = f"https://github.com/{repo_url}"
    if repo_url.endswith("/"):
        repo_url = repo_url.rstrip("/")

    ref = fields.get("ref", "").strip() or "main"
    subpath = fields.get("subpath", "").strip().rstrip("/")

    # Clone upstream to temp dir
    import tempfile
    with tempfile.TemporaryDirectory(prefix="add-skill-") as tmp:
        tmp_dir = Path(tmp) / "repo"
        try:
            git("clone", "--depth", "1", "--branch", ref, repo_url, str(tmp_dir))
        except RuntimeError as e:
            return {"success": False, "errors": [f"克隆仓库失败: {e}"]}

        # Determine skill source directory
        src_dir = tmp_dir / subpath if subpath else tmp_dir
        if not src_dir.is_dir():
            return {
                "success": False,
                "errors": [f"子目录 '{subpath}' 在仓库中不存在"],
            }

        # Find SKILL.md
        skill_md = src_dir / "SKILL.md"
        if not skill_md.exists():
            return {
                "success": False,
                "errors": [
                    f"未找到 SKILL.md — 确认仓库"
                    f"{'的 ' + subpath + ' 目录' if subpath else ''}"
                    " 中包含 SKILL.md"
                ],
            }

        # Parse frontmatter
        content = skill_md.read_text()
        fm = parse_frontmatter(content)
        if not fm or not fm.get("name"):
            return {"success": False, "errors": ["SKILL.md 缺少有效的 YAML frontmatter (name)"]}

        skill_name = str(fm["name"]).strip()
        skill_desc = str(fm.get("description", "")).strip()
        skill_id = skill_name.lower().replace(" ", "-")
        # Sanitize to kebab-case
        skill_id = re.sub(r"[^a-z0-9-]", "-", skill_id).strip("-")

        if not VALID_ID_RE.match(skill_id):
            return {"success": False, "errors": [f"无法从 name '{skill_name}' 生成合法的 skill ID"]}

        # Check uniqueness
        existing_ids = {s["id"] for s in hub.get("skills", []) if isinstance(s, dict)}
        if skill_id in existing_ids:
            return {"success": False, "errors": [f"Skill ID '{skill_id}' 已存在于 hub.yaml"]}

        # Auto-detect metadata
        license_name = detect_license(tmp_dir)
        author = detect_author(tmp_dir)

        # Copy skill files
        dst_dir = REPO_ROOT / skill_id
        print(f"  Copying {src_dir} → {dst_dir}")
        shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)

        # Register in hub.yaml
        head_sha = get_head_sha(tmp_dir)
        entry = {
            "id": skill_id,
            "type": "external",
            "path": skill_id,
            "description": skill_desc or f"Synced from {repo_url}",
            "source": {"repo": repo_url + ".git" if not repo_url.endswith(".git") else repo_url, "ref": ref},
            "last_synced": {
                "commit_sha": head_sha,
                "synced_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        }
        if subpath:
            entry["source"]["subpath"] = subpath + "/"

        metadata = {}
        if license_name:
            metadata["license"] = license_name
        if author:
            metadata["author"] = author
        if metadata:
            entry["metadata"] = metadata

        hub["skills"].append(entry)

        # Save hub.yaml
        with open(HUB_FILE, "w") as f:
            yaml.dump(hub, f)

        return {
            "success": True,
            "skill_id": skill_id,
            "skill_name": skill_name,
            "description": skill_desc,
            "license": license_name,
            "author": author,
            "files_count": sum(1 for _ in dst_dir.rglob("*") if _.is_file()),
        }


def get_head_sha(repo_dir: Path) -> str:
    return git("rev-parse", "HEAD", cwd=repo_dir)


# ── Main ───────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Add skill from Issue")
    parser.add_argument("--issue-body", type=Path, required=True)
    parser.add_argument("--issue-number", type=int, required=True)
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "_add_result.json")
    args = parser.parse_args()

    body = args.issue_body.read_text()
    fields = parse_issue_body(body)

    print("Parsed fields:")
    for k, v in fields.items():
        print(f"  {k}: {v}")

    with open(HUB_FILE) as f:
        hub = yaml.load(f)

    result = add_skill(fields, hub)

    if not result.get("success"):
        print(f"\n❌ Failed: {result.get('errors', [])}")
    else:
        print(f"\n✅ Skill '{result['skill_id']}' added!")
        print(f"  Name: {result.get('skill_name')}")
        print(f"  Description: {result.get('description', '')[:80]}")
        print(f"  License: {result.get('license', 'N/A')}")
        print(f"  Author: {result.get('author', 'N/A')}")
        print(f"  Files: {result.get('files_count', 0)}")

    result["issue_number"] = args.issue_number
    result["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
