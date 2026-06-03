# Skills Hub

A centralized collection of [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skills — 自写 + 外部收集，统一管理、自动同步。

## Skills

| Skill | Type | Author | Description |
|-------|------|--------|-------------|
| [code-review](code-review/) | 🏠 Local | — | 代码审查：SOLID、安全、并发、性能、代码质量 |
| [sigma](sigma/) | 🏠 Local | — | 1-on-1 AI 导师，Bloom's 2-Sigma 掌握式学习 |
| [skill-creator](skill-creator/) | 🏠 Local | — | 创建、评估、优化 Claude Code skills |
| [tdd](tdd/) | 🏠 Local | — | TDD 工作流：RED → GREEN → REFACTOR |
| [neat-freak](neat-freak/) | 🔗 External | Khazix | 会话结束后的文档与记忆洁癖级同步 |
| [bggg-skill-taotie](bggg-skill-taotie/) | 🔗 External | binggandata | Skill 进化器（饕餮）— 吞噬并分析其他 skill 优势 |
| [claude-design](claude-design/) | 🔗 External | dennistodo | 高保真 HTML 设计：落地页、PPT、原型、动画、海报 |
| [guizang-ppt-skill](guizang-ppt-skill/) | 🔗 External | 郭浩 | 横向翻页网页 PPT，电子杂志风 / 瑞士国际主义风 |

## 添加 Skill

### 通过 Issue（推荐）

1. 点击 **[Issues → New Issue → Add New Skill](../../issues/new?template=add-skill.yml)**
2. 只需填写一个字段：

| 字段 | 必填 | 说明 |
|------|------|------|
| 仓库地址 | ✅ | 上游 GitHub 仓库 URL |
| 子目录路径 | ❌ | 如果 skill 在仓库的某个子目录中 |
| 分支 / 标签 | ❌ | 不填则自动检测默认分支 |

3. 提交后自动完成：
   - 克隆上游 → 读取 `SKILL.md` 获取名称和描述
   - 自动检测 License 和 Author
   - 创建 PR → CI 校验 → 自动合并
   - Issue 自动关闭 ✅

**重试**：如果处理失败，修正问题后重新打开 Issue 即可重试。

### 手动添加

#### External Skill

在 `hub.yaml` 中添加条目，push 后下次同步自动拉取文件：

```yaml
- id: my-skill
  type: external
  path: my-skill
  description: "..."
  source:
    repo: https://github.com/org/repo.git
    ref: main          # 可选，默认自动检测
    subpath: path/     # 可选，只同步子目录
```

#### Local Skill

1. 创建目录和 `SKILL.md`（含 YAML frontmatter）
2. 在 `hub.yaml` 中注册：

```yaml
- id: my-skill
  type: local
  path: my-skill
  description: "What this skill does..."
```

## 自动同步

External skills 通过 GitHub Actions 自动保持最新。

| Workflow | 触发方式 | 说明 |
|----------|----------|------|
| Sync External Skills | 每天 02:00 UTC / 手动 | 检测上游更新 → 创建 PR → CI 通过后自动合并 |
| Add Skill from Issue | Issue 创建 / 重新打开 | 解析 Issue → 克隆上游 → 创建 PR → 自动合并 |
| Validate Skills | PR / Push | 校验 hub.yaml schema + SKILL.md frontmatter |
| Sync to Gitee | Push to main | 镜像到 Gitee |

### 手动触发同步

Actions → Sync External Skills → Run workflow：
- **dry_run**：只检测变更，不创建 PR
- **skill_id**：只同步指定 skill

## Gitee 镜像

每次 push 到 `main` 自动同步到 [Gitee](https://gitee.com/gclm/skills-hub)。

**配置**：GitHub 仓库 Settings → Secrets → 添加 `GITEE_TOKEN`（Gitee 个人访问令牌）

## 项目结构

```
skills-hub/
├── hub.yaml                          # 中心 manifest
├── scripts/
│   ├── validate.py                   # 校验 hub.yaml + SKILL.md
│   ├── sync_skills.py                # 同步外部 skill
│   └── add_skill_from_issue.py       # Issue 解析脚本
├── .github/
│   ├── workflows/
│   │   ├── validate.yml              # CI 校验
│   │   ├── sync-skills.yml           # 定时同步
│   │   ├── add-skill.yml             # Issue 处理
│   │   └── sync-gitee.yml            # Gitee 镜像
│   └── ISSUE_TEMPLATE/
│       └── add-skill.yml             # Issue 表单模板
├── <skill-name>/                     # 每个 skill 一个目录
│   └── SKILL.md                      # 核心 skill 定义
└── README.md
```

## License

MIT
