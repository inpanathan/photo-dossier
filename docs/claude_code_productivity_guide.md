# Claude Code Productivity Guide

How to work like Boris Cherny (Claude Code creator) and the Anthropic Claude Code team.

This guide distills workflows from Boris's public threads, the Claude Code team's tips, and official documentation into actionable practices for this project. Every section includes what this project already has configured and what you can do next.

---

## Table of Contents

1. [Philosophy](#1-philosophy)
2. [Setup: First-Time Configuration](#2-setup-first-time-configuration)
3. [The Plan-First Workflow](#3-the-plan-first-workflow)
4. [Parallel Execution](#4-parallel-execution)
5. [Skills: Automating Repeated Workflows](#5-skills-automating-repeated-workflows)
6. [Agents: Delegating Specialized Work](#6-agents-delegating-specialized-work)
7. [Hooks: Deterministic Lifecycle Integration](#7-hooks-deterministic-lifecycle-integration)
8. [Verification-Driven Development](#8-verification-driven-development)
9. [CLAUDE.md: Compounding Engineering](#9-claudemd-compounding-engineering)
10. [MCP Servers and External Integrations](#10-mcp-servers-and-external-integrations)
11. [Prompting Techniques](#11-prompting-techniques)
12. [Advanced Configuration](#12-advanced-configuration)
13. [Daily Workflow Cheat Sheet](#13-daily-workflow-cheat-sheet)
14. [What This Project Has vs. Boris's Setup](#14-what-this-project-has-vs-boriss-setup)
15. [References](#15-references)

---

## 1. Philosophy

Boris Cherny's core philosophy can be summarized in four principles:

1. **Plan before you code.** Most sessions start in Plan Mode. Iterate on the plan until it's solid, then switch to auto-accept and Claude usually one-shots the implementation.

2. **Parallelize everything.** The #1 productivity unlock is running 3-5 sessions simultaneously, each in its own git worktree. Boris landed 259 PRs in 30 days this way.

3. **Verify, don't trust.** Give Claude a way to verify its work — tests, browser checks, E2E validation. This 2-3x the quality of results.

4. **Compound learnings.** Every mistake Claude makes becomes a rule in CLAUDE.md. Knowledge accumulates across the team, not just one session.

> "There is no one correct way to use Claude Code. We intentionally build it so you can use it, customize it, and hack it however you like." — Boris Cherny

---

## 2. Setup: First-Time Configuration

### 2.1 CLAUDE.md as Institutional Memory

CLAUDE.md is the most important file in your project for Claude Code. It's Claude's "constitution" — the primary source of truth for how your codebase works.

**This project already has:** A comprehensive CLAUDE.md with commands, code style, architecture, patterns, workflow rules, skills list, requirements-driven development, and planning rules.

**What to do:** Treat it as a living document. Whenever you see Claude make a mistake, add a rule to prevent it next time. The whole team should contribute.

### 2.2 Pre-Approved Permissions

Instead of clicking "allow" repeatedly or using `--dangerously-skip-permissions`, pre-approve safe operations.

**This project already has** (in `.claude/settings.json`):
```json
{
  "permissions": {
    "allow": [
      "Bash(uv run *)",
      "Bash(git status*)",
      "Bash(git diff*)",
      "Bash(git log*)",
      "Bash(gh issue *)",
      "Bash(gh pr *)"
    ]
  }
}
```

**Customize further:** Run `/permissions` in Claude Code to add more patterns. Destructive operations (`git push`, `git reset`, `rm`) are intentionally excluded.

### 2.3 Terminal and Status Line

Configure your status line to show useful info while coding:

```
/statusline
```

This displays model, directory, remaining context, cost, and other metrics. Every team member at Anthropic customizes theirs differently.

**Recommended terminal:** The Claude Code team favors [Ghostty](https://ghostty.org/) for synchronized rendering, 24-bit color, and proper Unicode support.

### 2.4 Model and Effort Selection

Boris uses **Opus with thinking** for all tasks and sets effort to **High**:

```
/model
```

His reasoning: "less steering + better tool use = faster overall" despite higher token cost. For budget-conscious work:

| Task | Model | Effort |
|------|-------|--------|
| Complex architecture, multi-file changes | Opus | High |
| Standard coding, single feature | Sonnet | Medium |
| Exploration, search, quick lookups | Haiku | Low |

Subagents in this project default to Sonnet (configured in their frontmatter).

### 2.5 Personal Overrides

Copy the template to create your personal config:

```bash
cp .claude/CLAUDE.local.md.template .claude/CLAUDE.local.md
```

This file is gitignored. Use it for personal preferences like verbose test output, custom keybindings, or environment-specific notes.

---

## 3. The Plan-First Workflow

### 3.1 Plan Mode

**Enter Plan Mode:** Press `Shift+Tab` twice, or use `EnterPlanMode`.

In Plan Mode, Claude explores the codebase and designs an approach without making changes. Boris's pattern:

```
Plan Mode → Refine plan iteratively → Switch to auto-accept → Claude one-shots implementation
```

**This project enforces planning:** Every implementation must produce a plan in `coding-agent/plans/<N>-<feature>.md` before coding begins (see CLAUDE.md "Planning rule").

### 3.2 Iterating on Plans

Don't accept the first plan. Push back:

- "What are the trade-offs of this approach vs. X?"
- "This plan doesn't account for the edge case where Y happens"
- "Can you simplify step 3? It seems over-engineered"

### 3.3 Switching to Auto-Accept

Once the plan is solid, switch to auto-accept edits mode. Claude should be able to implement the plan in one shot since all decisions are already made.

### 3.4 Plan Review with a Second Session

A team practice: have one Claude session write the plan, then spin up a second session to review it as a "staff engineer." This catches issues before implementation begins.

---

## 4. Parallel Execution

**This is the #1 productivity unlock**, according to both Boris and the Claude Code team.

### 4.1 Git Worktrees

Each parallel session needs its own copy of the repo. Use worktrees:

```bash
# Launch Claude Code in a new worktree
claude --worktree feature-auth

# Or manually create worktrees
git worktree add .claude/worktrees/feature-auth -b feature-auth
cd .claude/worktrees/feature-auth
claude
```

### 4.2 Running 3-5 Sessions

Boris runs 5 local sessions + 5-10 web sessions simultaneously:

```
Terminal Tab 1: claude --worktree feature-ingestion
Terminal Tab 2: claude --worktree fix-parser-bug
Terminal Tab 3: claude --worktree add-catalog-tests
Terminal Tab 4: claude --worktree refactor-config
Terminal Tab 5: claude --worktree docs-update
```

Name your tabs for easy reference. Each session works independently with no merge conflicts.

### 4.3 Web Sessions

Use [claude.ai/code](https://claude.ai/code) for additional sessions that don't need local file access. Good for:
- Research and planning
- Code review of PRs
- Writing documentation

### 4.4 Mobile to Desktop Handoff

Start a session from the Claude iOS app in the morning, continue on desktop later:

```bash
# Transfer a session between devices
claude --teleport
```

### 4.5 Backgrounding Sessions

Background a long-running task and continue in the foreground:

```
# In Claude Code, press Ctrl+B to background a task
# Or use & in the prompt to run in background
```

---

## 5. Skills: Automating Repeated Workflows

Skills (slash commands) automate inner-loop workflows you do many times a day.

### 5.1 Available Project Skills

This project has 8 skills checked into `.claude/skills/`:

| Skill | Purpose |
|-------|---------|
| `/run-checks` | Full quality pipeline: lint, format, typecheck, tests |
| `/fix-issue 123` | Read issue, implement fix, write tests, create PR |
| `/add-endpoint POST /items create item` | Scaffold endpoint + models + tests |
| `/review-code src/api/` | Security and quality review (isolated context) |
| `/review-pr` | Review current branch changes against main |
| `/spec feature-name` | Interview-driven feature spec |
| `/explain-code src/utils/config.py` | Visual explanation with diagrams |
| `/sync-requirements` | Sync requirement controller JSONs |

### 5.2 Creating New Skills

If you do something more than once a day, make it a skill:

```bash
# Create .claude/skills/my-skill/SKILL.md
mkdir -p .claude/skills/my-skill
```

```markdown
---
name: my-skill
description: What this skill does and when to use it
disable-model-invocation: true
argument-hint: "[optional-args]"
---

Instructions for Claude when this skill is invoked.
$ARGUMENTS contains what the user passed after the skill name.
```

### 5.3 Isolated Execution with `context: fork`

For skills that produce verbose output (reviews, analysis), use `context: fork` to keep results out of your main conversation:

```yaml
---
name: review-code
context: fork
agent: Explore
allowed-tools: Read, Grep, Glob
---
```

This project's `/review-code` and `/review-pr` skills already use this pattern.

### 5.4 Pre-Computed Context in Skills

Include inline Bash in skills to pre-compute information (like git status) before Claude processes, reducing unnecessary tool calls:

```markdown
Current git status:
\`\`\`bash
git status --short
\`\`\`
```

---

## 6. Agents: Delegating Specialized Work

Agents (subagents) handle specialized tasks in isolated context windows. Claude automatically delegates based on the agent's `description` field.

### 6.1 Built-in Agents

| Agent | Model | Purpose |
|-------|-------|---------|
| Explore | Haiku | Fast codebase search and analysis (read-only) |
| Plan | Inherit | Research for plan mode |
| general-purpose | Inherit | Complex multi-step tasks |

### 6.2 Project Agents

This project has 8 custom agents in `.claude/agents/`:

| Agent | Role | Key Capability |
|-------|------|----------------|
| `code-reviewer` | Quality review | Proactive after code changes, persistent memory |
| `security-reviewer` | Vulnerability scanning | OWASP top 10, secrets exposure |
| `test-writer` | Write tests | Runs in isolated worktree |
| `qa-tester` | Coverage analysis | Persistent memory for patterns |
| `code-simplifier` | Post-implementation cleanup | Simplifies without changing behavior |
| `verify-app` | E2E verification | Starts server, tests endpoints, reports |
| `architecture-explorer` | Architecture mapping | System overview, data flow, extension guide |
| `product-manager` | Requirements clarification | Acceptance criteria in Given/When/Then |

### 6.3 Agent Memory

Agents with `memory: project` accumulate knowledge across sessions. After each run, the agent updates its memory directory (`.claude/agent-memory/<name>/MEMORY.md`) with patterns, recurring issues, and conventions it discovered.

**Project agents with memory:** `code-reviewer`, `qa-tester`

To leverage memory, prompt Claude:
```
Use the code-reviewer agent to review my changes, and check its memory for patterns it's seen before
```

### 6.4 Proactive Invocation

Agents with "Use proactively" in their description are automatically triggered by Claude. The `code-reviewer` agent triggers after code modifications without you asking.

### 6.5 Worktree Isolation

Agents with `isolation: worktree` run in a temporary git worktree. The `test-writer` uses this so test files are written in isolation, preventing conflicts with your ongoing work.

### 6.6 Boris's Key Agent Patterns

**code-simplifier:** Run after every feature implementation:
```
Use the code-simplifier agent to clean up the files I just changed
```

**verify-app:** Run before creating a PR:
```
Use the verify-app agent to do a full end-to-end check
```

### 6.7 Parallel Agent Research

Launch multiple agents simultaneously for independent research:
```
Use 5 subagents to explore the codebase: one for data pipelines, one for models,
one for API routes, one for configuration, and one for testing patterns
```

---

## 7. Hooks: Deterministic Lifecycle Integration

Hooks are shell scripts that run at specific points in Claude's lifecycle. Unlike CLAUDE.md rules (which are suggestions), hooks are deterministic — they always execute.

### 7.1 PostToolUse: Auto-Format Code

**This project has:** A PostToolUse hook that runs `ruff format` and `ruff check --fix` after every Edit/Write operation.

```json
{
  "PostToolUse": [{
    "matcher": "Edit|Write",
    "hooks": [{
      "type": "command",
      "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/format-python.sh"
    }]
  }]
}
```

Boris's team has the same pattern. Claude writes well-formatted code 90% of the time; the hook catches the remaining 10%.

### 7.2 PreToolUse: File Protection

**This project has:** A PreToolUse hook that blocks edits to `.env`, `uv.lock`, `.pre-commit-config.yaml`, and `.claude/settings.local.json`.

This prevents Claude from accidentally modifying sensitive files. Exit code 2 blocks the action and sends a message back to Claude.

### 7.3 SessionStart: Post-Compaction Reminders

**This project has:** A SessionStart hook with `compact` matcher that reminds Claude of key rules after context compaction:

```
Post-compaction reminder: use uv (not pip). Run uv run ruff check + mypy + pytest
before committing. Check CLAUDE.md for project commands and patterns.
```

### 7.4 Notification: Desktop Alerts

**This project has:** A Notification hook that sends a desktop notification when Claude needs attention (Linux `notify-send`).

### 7.5 Commit Gating (Advanced)

Boris's team uses a PreToolUse hook on `Bash(git commit*)` that checks whether tests have passed in the current session. If not, the commit is blocked and Claude enters a test-and-fix loop.

**To add this:** Create a hook script that checks for a `.test-passed` marker file:

```bash
# .claude/hooks/gate-commit.sh
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if echo "$COMMAND" | grep -q "git commit"; then
    if [ ! -f .claude/.test-passed ]; then
        echo "Blocked: Run tests before committing. Use /run-checks first." >&2
        exit 2
    fi
fi
exit 0
```

### 7.6 Stop Hooks

Use Stop hooks to nudge Claude when it reaches turn limits or to perform cleanup after long tasks.

---

## 8. Verification-Driven Development

> "Give Claude a way to verify its work. If Claude has that feedback loop, it will 2-3x the quality of the final result." — Boris Cherny

### 8.1 Why Verification Matters

Without verification, Claude generates plausible-looking code that may have subtle bugs. With verification, Claude iterates until the code actually works.

### 8.2 `/run-checks` for Quality Gates

After any code change:

```
/run-checks
```

This runs lint, format check, typecheck, and tests sequentially. On failure, it reports the issue and offers to fix it.

### 8.3 `verify-app` for End-to-End

Before creating a PR:

```
Use the verify-app agent to do a full end-to-end verification
```

This starts the server, hits endpoints, checks logs, runs integration tests, and produces a pass/fail report.

### 8.4 Pre-Commit Hooks as Safety Net

Even if you forget to verify, pre-commit hooks catch issues:
- `ruff` — linting and formatting
- `mypy` — type checking
- `detect-private-key` — secrets
- `check-added-large-files` — accidental model weight commits

### 8.5 Prompting for Verification

Force Claude to prove its work:

```
Prove to me this works by showing the behavior diff between main and this branch
```

```
Grill me on these changes and don't make a PR until I pass your test
```

---

## 9. CLAUDE.md: Compounding Engineering

### 9.1 Living Document Pattern

CLAUDE.md is updated multiple times per week by the whole team. The pattern:

1. Claude makes a mistake during a PR
2. Someone adds a rule to CLAUDE.md to prevent it
3. Claude never makes that mistake again
4. Knowledge compounds across all team members

### 9.2 Adding Learnings from Mistakes

When Claude does something wrong:

```
Add a rule to CLAUDE.md that prevents this mistake in the future
```

Or manually add to the relevant section (Code style, Patterns to follow, Workflow).

### 9.3 `@.claude` PR Review Integration

On GitHub, tag `@.claude` on pull request comments to add learnings directly to CLAUDE.md. The Claude Code GitHub Action commits the update automatically.

### 9.4 GitHub Action

Install the Claude Code GitHub Action for automated PR reviews:

```
/install-github-action
```

This enables:
- Automated code review on every PR
- CLAUDE.md updates from PR comments
- CI integration with Claude Code

### 9.5 Troubleshooting Guide

This project maintains `docs/troubleshooting.md` as institutional memory for debugging (REQ-AGT-004). After resolving non-trivial issues, document:
- Symptom
- Root cause
- Diagnostic commands used
- Resolution

---

## 10. MCP Servers and External Integrations

MCP (Model Context Protocol) servers give Claude access to external tools and data.

### 10.1 Slack Integration

Connect Slack to paste bug threads directly into Claude:

```json
{
  "mcpServers": {
    "slack": {
      "type": "http",
      "url": "https://slack.mcp.anthropic.com/mcp"
    }
  }
}
```

Boris's workflow: paste a Slack bug thread, say "fix." Zero context switching.

### 10.2 Database CLI Integration

Use database CLIs directly in Claude Code:

```
Query the database to find all users who signed up last week
```

Works with `bq` (BigQuery), `psql` (PostgreSQL), `sqlite3`, or any CLI tool. Boris: "I haven't written a line of SQL in 6+ months."

### 10.3 Sentry for Error Logs

Connect Sentry to retrieve error logs directly:
```
Check Sentry for the most recent errors in the ingestion pipeline
```

### 10.4 Configuring MCP Servers

Add MCP servers to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "server-name": {
      "type": "http",
      "url": "https://server.example.com/mcp"
    }
  }
}
```

Or install from the plugin marketplace: `/plugin`

---

## 11. Prompting Techniques

### 11.1 Claude as Reviewer

```
Grill me on these changes and don't make a PR until I pass your test
```

Claude becomes your code reviewer, asking hard questions about your implementation.

### 11.2 Behavior Diffs

```
Prove to me this works by showing the behavior diff between main and this branch
```

Forces Claude to demonstrate the actual impact of changes, not just describe them.

### 11.3 Elegant Solutions

After a mediocre first attempt:

```
Knowing everything you know now, scrap this and implement the elegant solution
```

Claude's second attempt, with full context from the first, is often dramatically better.

### 11.4 Detailed Specs

More specificity yields better output. Instead of "add auth," write:

```
Add JWT authentication to the /api/v1/sources endpoints. Use python-jose for
token validation. Tokens should have a 1-hour expiry. Store the secret key in
settings.auth.secret_key. Return 401 with ErrorCode.UNAUTHORIZED for invalid tokens.
```

### 11.5 Voice Dictation

Speak 3x faster than typing. On macOS, press `fn` twice to start dictation. Voice prompts naturally become more detailed, which produces better results.

---

## 12. Advanced Configuration

### 12.1 Pre-Approved Permissions

Run `/permissions` to manage which operations Claude can perform without asking:

```
/permissions
```

This project pre-allows: `uv run *`, `git status/diff/log/branch/stash`, `ls/cat/head/tail`, `gh issue/pr`.

### 12.2 Sandbox Mode

Enable sandboxing for improved safety:

```
/sandbox
```

Restricts file and network access while reducing permission prompts.

### 12.3 Output Style

Configure how Claude communicates:

```
/config
```

Options:
- **Explanatory**: Claude explains the "why" behind changes
- **Learning**: Claude coaches through modifications
- **Custom**: Create your own voice and formatting rules

### 12.4 Keybindings

Customize every keybinding:

```
/keybindings
```

Settings live-reload for immediate feedback.

### 12.5 Plugins

Browse and install plugins from the marketplace:

```
/plugin
```

Plugins can install LSPs, MCP servers, skills, agents, and hooks. Create a company marketplace for internal tools.

### 12.6 Settings Checked into Git

This project checks `.claude/settings.json` into git so the whole team benefits from shared configurations (permissions, hooks, MCP servers). Personal overrides go in `.claude/settings.local.json` (gitignored).

---

## 13. Daily Workflow Cheat Sheet

### Morning Startup

```bash
# 1. Start Claude Code
claude

# 2. Check status line is configured
/statusline

# 3. Set model preference
/model   # Select Opus + High effort for the day
```

### Feature Development Loop

```bash
# 1. Create a worktree session
claude --worktree feature-name

# 2. Start in Plan Mode (Shift+Tab x2)
# "Plan how to implement <feature> based on the requirements"

# 3. Iterate on plan until solid

# 4. Switch to auto-accept, let Claude implement

# 5. Verify
/run-checks

# 6. Simplify
# "Use the code-simplifier agent on the files I changed"

# 7. Final verification
# "Use the verify-app agent for E2E check"
```

### Bug Fix Loop

```bash
# 1. Read the issue
/fix-issue 42

# Claude: reads issue → finds root cause → implements fix → writes tests → runs checks → commits → creates PR
```

### PR Review Loop

```bash
# 1. Review current branch
/review-pr

# 2. Or review specific code
/review-code src/data/ingestion.py
```

### End of Day

```bash
# 1. Check for any unfinished work
# "Summarize what we accomplished and what's still pending"

# 2. If mid-task, save progress
# Claude writes to .claude/scratchpad/<branch-name>.md automatically

# 3. Update CLAUDE.md if we learned something new
# "Add a rule to CLAUDE.md about <the thing we discovered>"
```

---

## 14. What This Project Has vs. Boris's Setup

| Practice | Status | Notes |
|----------|--------|-------|
| CLAUDE.md as living doc | Implemented | Commands, style, architecture, patterns, workflow, planning |
| Plan-first workflow | Implemented | Planning rule enforced, plans in `coding-agent/plans/` |
| PostToolUse formatting | Implemented | ruff format + check after Edit/Write |
| PreToolUse file protection | Implemented | Blocks .env, uv.lock, settings.local.json |
| Post-compaction reminders | Implemented | SessionStart hook with compact matcher |
| Desktop notifications | Implemented | notify-send on Notification events |
| Slash commands/skills | Implemented | 8 skills: run-checks, fix-issue, add-endpoint, etc. |
| Custom agents | Implemented | 8 agents: code-reviewer, security-reviewer, test-writer, etc. |
| Pre-approved permissions | Implemented | Safe ops pre-allowed in settings.json |
| Agent memory | Implemented | code-reviewer, qa-tester have project memory |
| Proactive agent invocation | Implemented | code-reviewer triggers after code changes |
| Worktree isolation | Implemented | test-writer runs in isolated worktree |
| Code simplifier | Implemented | Post-implementation cleanup agent |
| verify-app agent | Implemented | E2E verification before PR |
| Worktree guidance | Documented | CLAUDE.md + this guide |
| Model selection guidance | Documented | CLAUDE.md + this guide |
| GitHub Action (@.claude) | Not yet | Run `/install-github-action` to set up |
| MCP servers | Not yet | Configure in settings.json per Section 10 |
| Commit gating hook | Not yet | See Section 7.5 for implementation |

---

## 15. References

### Boris Cherny's Workflow

- [Complete Workflow Aggregation — howborisusesclaudecode.com](https://howborisusesclaudecode.com/)
- [Thread Part 1 — Personal Setup (Jan 2, 2026)](https://www.threads.com/@boris_cherny/post/DTBVlMIkpcm/)
- [Thread Part 2 — Team Tips (Jan 31, 2026)](https://www.threads.com/@boris_cherny/post/DUMZr4VElyb/)
- [Boris Cherny's 22 Tips — Medium](https://medium.com/@joe.njenga/boris-cherny-claude-code-creator-shares-these-22-tips-youre-probably-using-it-wrong-1b570aedefbe)
- [InfoQ — Inside the Development Workflow of Claude Code's Creator](https://www.infoq.com/news/2026/01/claude-code-creator-workflow/)
- [VentureBeat — Creator Revealed His Workflow](https://venturebeat.com/technology/the-creator-of-claude-code-just-revealed-his-workflow-and-developers-are)
- [How Boris Uses Claude Code — Karo Zieminski](https://karozieminski.substack.com/p/boris-cherny-claude-code-workflow)
- [How the Creator Uses Claude Code — Paddo](https://paddo.dev/blog/how-boris-uses-claude-code/)
- [How the Creator Actually Uses Claude Code — Push to Prod](https://getpushtoprod.substack.com/p/how-the-creator-of-claude-code-actually)

### Claude Code Official Documentation

- [Claude Code Overview & Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Custom Subagents Documentation](https://code.claude.com/docs/en/sub-agents)
- [Skills Documentation](https://code.claude.com/docs/en/skills)
- [Hooks Documentation](https://code.claude.com/docs/en/hooks)
- [Permissions Documentation](https://code.claude.com/docs/en/permissions)
- [MCP Servers Documentation](https://code.claude.com/docs/en/mcp)
- [Settings Documentation](https://code.claude.com/docs/en/settings)
- [Common Workflows](https://code.claude.com/docs/en/common-workflows)
- [Agent Teams Documentation](https://code.claude.com/docs/en/agent-teams)
- [Plugins Documentation](https://code.claude.com/docs/en/plugins)
- [Claude Code in Action — Anthropic Course](https://anthropic.skilljar.com/claude-code-in-action)

### Community Guides and Resources

- [10 Tips from Inside the Claude Code Team — Paddo](https://paddo.dev/blog/claude-code-team-tips/)
- [Claude Code Customization Guide — alexop.dev](https://alexop.dev/posts/claude-code-customization-guide-claudemd-skills-subagents/)
- [Understanding Claude Code's Full Stack — alexop.dev](https://alexop.dev/posts/understanding-claude-code-full-stack/)
- [How I Use Every Claude Code Feature — Shrivu Shankar](https://blog.sshh.io/p/how-i-use-every-claude-code-feature)
- [Best Practices for Claude Code Subagents — PubNub](https://www.pubnub.com/blog/best-practices-for-claude-code-sub-agents/)
- [awesome-claude-code — GitHub](https://github.com/hesreallyhim/awesome-claude-code)
- [awesome-claude-code-subagents — VoltAgent GitHub](https://github.com/VoltAgent/awesome-claude-code-subagents)
- [Claude Code Showcase — ChrisWiles GitHub](https://github.com/ChrisWiles/claude-code-showcase)
- [Claude Code Best Practices — awattar GitHub](https://github.com/awattar/claude-code-best-practices)
- [Claude Code Explained — Medium](https://avinashselvam.medium.com/claude-code-explained-claude-md-command-skill-md-hooks-subagents-e38e0815b59b)
- [A Guide to Claude Code 2.0 — sankalp](https://sankalp.bearblog.dev/my-experience-with-claude-code-20-and-how-to-get-better-at-using-coding-agents/)
- [Understanding Skills vs Commands vs Subagents vs Plugins](https://www.youngleaders.tech/p/claude-skills-commands-subagents-plugins)
- [Advanced Claude Code Tips — Cuttlesoft](https://cuttlesoft.com/blog/2026/02/03/claude-code-for-advanced-users/)
