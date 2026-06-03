# Skills Hub

A centralized collection of [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skills.

## Skills

| Skill | Type | Description |
|-------|------|-------------|
| [code-review](code-review/) | Local | Expert code review with SOLID, security, and performance checks |
| [sigma](sigma/) | Local | 1-on-1 AI tutor using Bloom's 2-Sigma mastery learning |
| [skill-creator](skill-creator/) | Local | Create, evaluate, and optimize Claude Code skills |
| [tdd](tdd/) | Local | Test-Driven Development workflow with Go/Java/Python examples |

## hub.yaml

The `hub.yaml` file is the single source of truth for all skills. It tracks:

- **Local skills** — self-written, no upstream source
- **External skills** — synced from upstream repositories, with version tracking
- **Last synced version** (commit SHA) for each external skill

## Adding a New Skill

### Option A: Submit an Issue (Recommended)

1. Go to **Issues → New Issue → Add New Skill**
2. Fill in the form:
   - **Skill Type**: Local (self-written) or External (from upstream repo)
   - **Skill ID**: kebab-case identifier (e.g., `my-new-skill`)
   - **Description**: What the skill does and when to trigger
   - **Upstream info** (External only): repo URL, branch/tag, optional subpath
   - **SKILL.md content** (Local only): paste the full SKILL.md with frontmatter
3. Submit — a PR will be created automatically. It merges after CI validation passes.

### Option B: Manual

#### Adding a Local Skill

1. Create a directory and `SKILL.md`:

```yaml
# my-new-skill/SKILL.md
---
name: my-new-skill
description: "What this skill does and when to trigger it."
when_to_use: "When this skill should activate"
---
```

2. Add optional `references/`, `agents/`, `scripts/` as needed.
3. Register in `hub.yaml`:

```yaml
skills:
  - id: my-new-skill
    type: local
    path: my-new-skill
    description: "What this skill does..."
```

#### Registering an External Skill

Add an entry to `hub.yaml` with the upstream source:

```yaml
# Whole repo = one skill
skills:
  - id: upstream-skill
    type: external
    path: upstream-skill
    source:
      repo: https://github.com/org/repo.git
      ref: main
    metadata:
      license: MIT
      author: "Author Name"

# Subdirectory = one skill
  - id: subdir-skill
    type: external
    path: subdir-skill
    source:
      repo: https://github.com/org/big-repo.git
      ref: main
      subpath: skills/my-skill/
```

Commit and push — the sync workflow will pull the skill content on the next run.

## Sync Workflow

External skills are automatically synced via GitHub Actions.

| Trigger | Schedule |
|---------|----------|
| Scheduled | Every day at 02:00 UTC |
| Manual | Actions → Sync External Skills → Run workflow |

### How It Works

1. The workflow reads `hub.yaml` and checks each external skill's upstream repo.
2. If the upstream commit SHA differs, it compares file contents.
3. If changes are found, it copies updated files and creates a PR.
4. The validation workflow runs on the PR to verify format.
5. If validation passes, the PR is auto-merged.

### Manual Trigger Options

- **dry_run**: Detect changes without creating a PR
- **skill_id**: Sync only a specific skill (by id)

## Validation

Every PR is validated by CI:

- `hub.yaml` schema: required fields, valid types, no duplicate ids
- `SKILL.md` frontmatter: `name` and `description` are required
- Cross-reference: every skill directory is listed in `hub.yaml` and vice versa

## Gitee Mirror

This repository automatically mirrors to [Gitee](https://gitee.com/gclm/skillhub) on every push to `main`.

**Setup required**: Add `GITEE_SSH_PRIVATE_KEY` to GitHub repository secrets (Settings → Secrets and variables → Actions) with your Gitee SSH private key.

## License

MIT
