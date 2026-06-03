#!/usr/bin/env python3
"""Sync external skills from upstream repositories.

Reads hub.yaml, checks each external skill for upstream changes,
copies updated files, and produces a change report.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
HUB_FILE = REPO_ROOT / "hub.yaml"

yaml = YAML()
yaml.preserve_quotes = True
yaml.default_flow_style = False


# ── Helpers ────────────────────────────────────────────────────────


def git(*args: str, cwd: Path | None = None, check: bool = True) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def get_head_sha(repo_dir: Path) -> str:
    """Get the HEAD commit SHA of a cloned repo."""
    return git("rev-parse", "HEAD", cwd=repo_dir)


def file_hashes(directory: Path) -> dict[str, str]:
    """Return {relative_path: hash} for all files in directory."""
    hashes: dict[str, str] = {}
    for root, _, files in os.walk(directory):
        for fname in files:
            fpath = Path(root) / fname
            rel = str(fpath.relative_to(directory))
            # Simple hash: use file size + first/last 1KB as fingerprint
            stat = fpath.stat()
            with open(fpath, "rb") as f:
                head = f.read(1024)
                f.seek(max(0, stat.st_size - 1024))
                tail = f.read(1024)
            hashes[rel] = f"{stat.st_size}:{hash(head + tail)}"
    return hashes


def sync_directory(src: Path, dst: Path) -> dict:
    """Sync src into dst (rsync-style). Returns change summary."""
    src_hashes = file_hashes(src)
    dst_hashes = file_hashes(dst) if dst.exists() else {}

    added = sorted(set(src_hashes) - set(dst_hashes))
    removed = sorted(set(dst_hashes) - set(src_hashes))
    modified = sorted(
        p for p in set(src_hashes) & set(dst_hashes)
        if src_hashes[p] != dst_hashes[p]
    )

    # Apply changes
    if not dst.exists():
        dst.mkdir(parents=True, exist_ok=True)

    # Copy added/modified
    for rel in added + modified:
        src_file = src / rel
        dst_file = dst / rel
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst_file)

    # Remove deleted
    for rel in removed:
        dst_file = dst / rel
        if dst_file.exists():
            dst_file.unlink()
            # Clean up empty parent dirs
            parent = dst_file.parent
            while parent != dst and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent

    return {
        "files_added": added,
        "files_modified": modified,
        "files_deleted": removed,
        "has_changes": bool(added or modified or removed),
    }


# ── Core sync logic ───────────────────────────────────────────────


def sync_skill(skill: dict, dry_run: bool = False) -> dict | None:
    """Sync a single external skill. Returns change summary or None if unchanged."""
    sid = skill["id"]
    source = skill.get("source", {})
    repo_url = source.get("repo", "")
    ref = source.get("ref", "main")
    subpath = source.get("subpath", "")

    last_sha = ""
    ls = skill.get("last_synced")
    if isinstance(ls, dict):
        last_sha = str(ls.get("commit_sha", ""))

    if not repo_url:
        print(f"  ⚠️  {sid}: no source.repo, skipping")
        return None

    # Clone upstream
    with tempfile.TemporaryDirectory(prefix=f"sync-{sid}-") as tmp:
        tmp_dir = Path(tmp) / "repo"
        try:
            git("clone", "--depth", "1", "--branch", ref, repo_url, str(tmp_dir))
        except RuntimeError as e:
            print(f"  ❌ {sid}: clone failed — {e}")
            return None

        new_sha = get_head_sha(tmp_dir)

        # Same SHA → nothing to do
        if new_sha == last_sha:
            print(f"  ✓  {sid}: up to date ({new_sha[:8]})")
            return None

        # Determine source directory
        if subpath:
            src_dir = tmp_dir / subpath.rstrip("/")
        else:
            src_dir = tmp_dir

        if not src_dir.is_dir():
            print(f"  ⚠️  {sid}: subpath '{subpath}' not found in upstream")
            return None

        # Check SKILL.md exists
        if not (src_dir / "SKILL.md").exists():
            print(f"  ⚠️  {sid}: no SKILL.md in upstream source, skipping")
            return None

        # Compare and sync files
        dst_dir = REPO_ROOT / skill["path"]
        changes = sync_directory(src_dir, dst_dir) if not dry_run else {
            "files_added": [],
            "files_modified": [],
            "files_deleted": [],
            "has_changes": True,  # assume changes in dry-run
        }

        if not changes["has_changes"] and not dry_run:
            # SHA changed but files are the same (change was outside skill)
            print(f"  ✓  {sid}: SHA changed but files identical, updating ref only")
        elif changes["has_changes"]:
            n = len(changes["files_added"]) + len(changes["files_modified"])
            d = len(changes["files_deleted"])
            print(f"  📥 {sid}: {n} file(s) changed, {d} removed ({last_sha[:8]} → {new_sha[:8]})")

        # Update last_synced in the skill dict (in memory)
        if not dry_run:
            skill["last_synced"] = {
                "commit_sha": new_sha,
                "synced_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

        return {
            "id": sid,
            "old_sha": last_sha,
            "new_sha": new_sha,
            **changes,
        }


# ── Main ───────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync external skills")
    parser.add_argument("--hub-file", type=Path, default=HUB_FILE,
                        help="Path to hub.yaml")
    parser.add_argument("--dry-run", action="store_true",
                        help="Detect changes but do not write")
    parser.add_argument("--skill", type=str, default=None,
                        help="Sync only this skill (by id)")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "_sync_output.json",
                        help="Path for JSON change report")
    args = parser.parse_args()

    # Load hub.yaml
    with open(args.hub_file) as f:
        hub = yaml.load(f)

    if not hub or "skills" not in hub:
        print("❌ Invalid hub.yaml: no skills list")
        return 1

    # Filter external skills
    external = [s for s in hub["skills"] if s.get("type") == "external"]
    if args.skill:
        external = [s for s in external if s.get("id") == args.skill]
        if not external:
            print(f"❌ No external skill with id '{args.skill}'")
            return 1

    if not external:
        print("No external skills to sync.")
        return 0

    print(f"Syncing {len(external)} external skill(s)...\n")

    # Sync each skill
    changed: list[dict] = []
    unchanged: list[str] = []

    for skill in external:
        result = sync_skill(skill, dry_run=args.dry_run)
        if result and result.get("has_changes"):
            changed.append(result)
        elif result is None:
            unchanged.append(skill["id"])
        else:
            unchanged.append(skill["id"])

    # Write updated hub.yaml (preserves comments and formatting)
    if not args.dry_run and changed:
        with open(args.hub_file, "w") as f:
            yaml.dump(hub, f)

    # Write change report
    report = {
        "synced_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dry_run": args.dry_run,
        "skills_changed": changed,
        "skills_unchanged": unchanged,
        "total_changes": len(changed),
    }

    with open(args.output, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Done: {len(changed)} changed, {len(unchanged)} unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
