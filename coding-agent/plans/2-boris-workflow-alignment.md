# Plan: Boris/Claude Team Workflow Alignment + User Productivity Guide

## Context

Research comparing Boris Cherny's (Claude Code creator) workflows and the Anthropic Claude Code team's practices against this project identified 14 gaps. This plan addresses all gaps through code changes and a comprehensive user guide that teaches the developer to work like Boris and the team.

**Two deliverables:**
1. Code changes to close the workflow gaps (settings, agents, CLAUDE.md)
2. A comprehensive user guide: `docs/claude_code_productivity_guide.md`

---

## Status

- [x] Phase 1: Settings & Permissions
- [x] Phase 2: New/Updated Agents
- [x] Phase 3: CLAUDE.md Updates
- [x] Phase 4: User Productivity Guide
- [x] Phase 5: Apply to Template
- [x] Phase 6: Verification

---

## Changes Summary

| # | File | Action |
|---|------|--------|
| 1 | `.claude/settings.json` | Modify — add `permissions.allow` block |
| 2 | `.claude/agents/code-reviewer.md` | Modify — add `memory: project`, proactive description |
| 3 | `.claude/agents/qa-tester.md` | Modify — add `memory: project` |
| 4 | `.claude/agents/test-writer.md` | Modify — add `isolation: worktree` |
| 5 | `.claude/agents/code-simplifier.md` | Create — post-implementation cleanup agent |
| 6 | `.claude/agents/verify-app.md` | Create — E2E verification agent |
| 7 | `CLAUDE.md` | Modify — add worktree workflow, model guidance |
| 8 | `.claude/CLAUDE.local.md.template` | Modify — add model/effort preferences |
| 9 | `docs/claude_code_productivity_guide.md` | Create — comprehensive user guide |
| 10 | Apply changes 1–9 to `ai-ml-project-template` | Copy/adapt |

**2 new files, 7 modifications, applied to both projects.**

---

## Phase 1: Settings & Permissions

### 1. Modify `.claude/settings.json`

Add pre-approved permissions for safe, frequently-used operations. This eliminates repetitive permission prompts without sacrificing safety.

**Add `permissions` block:**

```json
{
  "permissions": {
    "allow": [
      "Bash(uv run *)",
      "Bash(git status*)",
      "Bash(git diff*)",
      "Bash(git log*)",
      "Bash(git branch*)",
      "Bash(git stash*)",
      "Bash(ls *)",
      "Bash(cat *)",
      "Bash(head *)",
      "Bash(tail *)",
      "Bash(wc *)",
      "Bash(echo *)",
      "Bash(which *)",
      "Bash(gh issue *)",
      "Bash(gh pr *)",
      "Read",
      "Glob",
      "Grep"
    ]
  }
}
```

**Rationale:** Boris uses `/permissions` to pre-allow common operations. These are all read-only or safe build/test commands. `git commit`, `git push`, `git reset`, `rm`, `Edit`, `Write` are intentionally excluded — they require explicit approval.

---

## Phase 2: New/Updated Agents (5 files)

### 2. Modify `.claude/agents/code-reviewer.md`

Changes:
- Add `memory: project` to frontmatter — accumulates patterns and recurring issues across sessions
- Update description to include "Use proactively after writing or modifying code" for automatic delegation
- Add memory instructions to the system prompt

### 3. Modify `.claude/agents/qa-tester.md`

Changes:
- Add `memory: project` — accumulates coverage gaps and test quality patterns over time

### 4. Modify `.claude/agents/test-writer.md`

Changes:
- Add `isolation: worktree` — writes tests in an isolated copy, preventing conflicts with ongoing work

### 5. Create `.claude/agents/code-simplifier.md`

**Tools:** Read, Edit, Write, Grep, Glob, Bash | **Model:** sonnet

Post-implementation cleanup agent (inspired by Boris's `code-simplifier`):
- Removes dead code, redundant variables, unused imports
- Simplifies overly complex conditionals and deeply nested logic
- Deduplicates repeated patterns into shared helpers (only when 3+ occurrences)
- Ensures consistent naming and formatting
- Runs `uv run ruff check --fix` and `uv run ruff format` after changes
- Does NOT change behavior — only refactors for clarity
- Output: list of changes made with before/after snippets

### 6. Create `.claude/agents/verify-app.md`

**Tools:** Read, Bash, Grep, Glob | **Model:** sonnet

End-to-end verification agent (inspired by Boris's `verify-app`):
- Starts the dev server (`bash scripts/start_server.sh`)
- Hits the health endpoint to verify it's running
- Exercises key API endpoints with `curl`/`httpx`
- Checks structured log output for errors
- Runs the integration test suite
- Stops the server and reports results
- Output: Pass/Fail checklist with details on any failures

---

## Phase 3: CLAUDE.md Updates

### 7. Modify `CLAUDE.md` — Workflow section

Add to the Workflow section:

```markdown
- **Parallel sessions**: For independent tasks, use `claude --worktree <name>` to run isolated sessions with separate git worktrees. Each session gets its own copy of the repo — no merge conflicts
- **Model selection**: Use Opus for complex multi-file architectural work. Subagents default to Sonnet (fast, cost-effective). Use Haiku for exploration-only agents
- **Verification**: After implementation, use the `verify-app` agent or `/run-checks` to validate before committing. Give Claude a way to verify its work — this 2-3x the quality of results
- **Post-implementation cleanup**: Use the `code-simplifier` agent after completing a feature to reduce complexity before the PR
```

### 8. Modify `.claude/CLAUDE.local.md.template`

Add model and effort preference section with concrete examples:

```markdown
## Model preferences
# - Set effort to High for all tasks: /model → High
# - Use Opus with thinking for complex architectural work
# - Use Sonnet for standard coding tasks

## Parallel workflow
# - I run 3-5 worktree sessions in parallel
# - Tab naming convention: 1-feature, 2-tests, 3-bugfix
# - Start mobile sessions from Claude iOS app, continue on desktop
```

---

## Phase 4: User Productivity Guide

### 9. Create `docs/claude_code_productivity_guide.md`

Comprehensive guide organized by workflow stage, teaching the user to work like Boris and the Claude Code team. All practices are grounded in specific references.

**Outline:**

```
# Claude Code Productivity Guide

## Table of Contents
1. Philosophy: How Boris and the Claude Code Team Work
2. Setup: First-Time Configuration
   2.1. CLAUDE.md as institutional memory
   2.2. Pre-approved permissions (settings.json)
   2.3. Terminal and status line (/statusline)
   2.4. Model and effort selection (/model)
   2.5. Personal overrides (CLAUDE.local.md)
3. The Plan-First Workflow
   3.1. Plan mode (Shift+Tab ×2)
   3.2. Iterating on plans
   3.3. Switching to auto-accept mode
   3.4. Plan review with a second session
4. Parallel Execution (The #1 Productivity Unlock)
   4.1. Git worktrees: claude --worktree <name>
   4.2. Running 3-5 sessions simultaneously
   4.3. Web sessions on claude.ai/code
   4.4. Mobile → Desktop handoff with --teleport
   4.5. Backgrounding sessions with &
5. Skills: Automating Repeated Workflows
   5.1. Available project skills (/run-checks, /fix-issue, etc.)
   5.2. Creating new skills (.claude/skills/)
   5.3. context: fork for isolated execution
   5.4. Inline bash in skills for pre-computed context
6. Agents: Delegating Specialized Work
   6.1. Built-in agents (Explore, Plan, general-purpose)
   6.2. Project agents (code-reviewer, security-reviewer, etc.)
   6.3. Agent memory for cross-session learning
   6.4. Proactive invocation via descriptions
   6.5. Worktree isolation for safe parallel agents
   6.6. The code-simplifier and verify-app patterns
   6.7. Parallel research: "use 5 subagents to explore"
7. Hooks: Deterministic Lifecycle Integration
   7.1. PostToolUse formatting hook
   7.2. PreToolUse file protection hook
   7.3. Post-compaction reminders (SessionStart)
   7.4. Desktop notifications (Notification)
   7.5. Commit gating with PreToolUse on Bash(git commit)
   7.6. Stop hooks for turn-limit nudges
8. Verification-Driven Development
   8.1. Why verification 2-3x quality
   8.2. /run-checks for lint + type + tests
   8.3. verify-app agent for E2E
   8.4. Pre-commit hooks as safety net
   8.5. "Prove to me this works" prompting
9. CLAUDE.md: Compounding Engineering
   9.1. Living document pattern
   9.2. Adding learnings from mistakes
   9.3. @.claude PR review integration
   9.4. GitHub Action (/install-github-action)
   9.5. Troubleshooting guide as institutional memory
10. MCP Servers and External Integrations
    10.1. Slack MCP for bug threads
    10.2. Database CLI integration (bq, psql)
    10.3. Sentry for error logs
    10.4. Configuring MCP servers in settings.json
11. Prompting Techniques for Better Results
    11.1. "Grill me on these changes" — Claude as reviewer
    11.2. "Prove to me this works" — behavior diffs
    11.3. "Scrap this and implement the elegant solution"
    11.4. Detailed specs reduce ambiguity
    11.5. Voice dictation (fn×2 on macOS)
12. Advanced Configuration
    12.1. /permissions for pre-approving operations
    12.2. /sandbox for improved safety
    12.3. /config for output style (explanatory, learning, custom)
    12.4. /keybindings for key customization
    12.5. /plugin for marketplace browsing
    12.6. settings.json checked into git for team sharing
13. Workflow Cheat Sheet (Daily Reference)
    13.1. Morning startup routine
    13.2. Feature development loop
    13.3. Bug fix loop
    13.4. PR creation and review loop
    13.5. End-of-day wrap-up
14. What This Project Has vs. Boris's Setup (Gap Tracker)
15. References
```

**Section 15 (References) will include all sources:**

```markdown
## 15. References

### Boris Cherny's Workflow
- [Complete Workflow Aggregation](https://howborisusesclaudecode.com/)
- [Thread Part 1 — Jan 2026](https://www.threads.com/@boris_cherny/post/DTBVlMIkpcm/)
- [Thread Part 2 — Jan 2026](https://www.threads.com/@boris_cherny/post/DUMZr4VElyb/)
- [Boris Cherny's 22 Tips — Medium](https://medium.com/@joe.njenga/boris-cherny-claude-code-creator-shares-these-22-tips...)
- [InfoQ — Inside the Development Workflow](https://www.infoq.com/news/2026/01/claude-code-creator-workflow/)
- [VentureBeat — Creator Revealed His Workflow](https://venturebeat.com/technology/the-creator-of-claude-code...)

### Claude Code Documentation
- [Claude Code Subagents](https://code.claude.com/docs/en/sub-agents)
- [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Claude Code Skills](https://code.claude.com/docs/en/skills)
- [Claude Code Hooks](https://code.claude.com/docs/en/hooks)
- [Claude Code Permissions](https://code.claude.com/docs/en/permissions)
- [Claude Code MCP Servers](https://code.claude.com/docs/en/mcp)

### Community Guides
- [How Boris Uses Claude Code — Karo Zieminski](https://karozieminski.substack.com/p/boris-cherny-claude-code-workflow)
- [10 Tips from Inside the Claude Code Team — Paddo](https://paddo.dev/blog/claude-code-team-tips/)
- [Claude Code Customization Guide — alexop.dev](https://alexop.dev/posts/claude-code-customization-guide...)
- [How I Use Every Claude Code Feature — Shrivu Shankar](https://blog.sshh.io/p/how-i-use-every-claude-code-feature)
- [Best Practices for Subagents — PubNub](https://www.pubnub.com/blog/best-practices-for-claude-code-sub-agents/)
- [awesome-claude-code — GitHub](https://github.com/hesreallyhim/awesome-claude-code)
```

---

## Phase 5: Apply to Template

### 10. Copy all changes to `ai-ml-project-template`

- Copy modified `settings.json`, agents, `CLAUDE.md`, `CLAUDE.local.md.template`
- Copy `docs/claude_code_productivity_guide.md` (remove Knowledge Hub-specific references)
- Copy the plan file

---

## Phase 6: Verification

1. `cat .claude/settings.json | jq .permissions` — verify permissions block exists
2. `grep -l "memory:" .claude/agents/*.md` — should show code-reviewer, qa-tester
3. `grep -l "isolation:" .claude/agents/*.md` — should show test-writer
4. `grep "proactively" .claude/agents/code-reviewer.md` — verify proactive description
5. `ls .claude/agents/*.md | wc -l` — should show 8 agents
6. `test -f docs/claude_code_productivity_guide.md` — verify guide exists
7. Verify guide has all 15 sections
8. Verify References section has all source links
9. Run same checks on `ai-ml-project-template`

---

## Implementation Order

1. Phase 1 (settings) — 1 file
2. Phase 2 (agents) — 5 files
3. Phase 3 (CLAUDE.md + template) — 2 files
4. Phase 4 (productivity guide) — 1 file, largest effort
5. Phase 5 (apply to template)
6. Phase 6 (verification)

Estimated: ~10 files modified/created per project, guide is ~800-1000 lines.
