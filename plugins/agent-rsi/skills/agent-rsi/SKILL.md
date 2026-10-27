---
name: agent-rsi
description: >
  Agent retrospective and self-improvement loop. Run at the end of any task that changed code, docs, config, pull requests, or deployments, and whenever a task failed, was redone, or the user corrected you. Records what worked and what failed, turns each failure into regression tests, an ADR, and a postmortem, counts repeated mistakes in agent-docs/ledger.md, and promotes repeated mistakes and proven methods into the right AGENTS.md. Triggers: "复盘", "总结经验", "postmortem", "retro", "RSI", "沉淀", or a Stop hook asking for a retrospective.
---

# Agent RSI (retrospective → self-improvement)

Goal: each mistake happens at most twice. The first time it is recorded. The second time it becomes a rule that every agent loads.

Keep it small. A retrospective that takes longer than the task is waste. For a clean, routine task, step 1 is enough.

## Where things go

The **workspace** is the directory the session started in: the one holding the top-level `AGENTS.md` for this work. Its `agent-docs/` directory holds the ledger and shared lessons. If `agent-docs/` does not exist, create it from `templates/agent-docs-README.md` and `templates/ledger.md`.

| Artifact | Location | When |
| --- | --- | --- |
| Regression unit / integration test | The affected repo, next to the code, in the same PR as the fix | Every bug that reached a commit, review, CI, or production |
| ADR | `<repo>/docs/adr/NNNN-<slug>.md` | A design choice that someone would later question or undo |
| Postmortem | `<repo>/docs/postmortems/YYYY-MM-DD-<slug>.md` if repo-specific; `agent-docs/postmortems/` if cross-repo or about agent process | Failure that reached CI, a reviewer, the user, or production; or cost more than ~30 min |
| Shared lesson | `agent-docs/lessons/<topic>.md` | Knowledge another agent in another repo of this workspace would also need |
| Counter | `agent-docs/ledger.md` | Every failure, and every proven method |
| Rule | See "Rule scope" below | Ledger count reaches 2, or a method proved itself twice |

Templates are in `templates/` next to this file. Repo files (tests, ADRs, repo postmortems, repo `AGENTS.md`) go through the task's branch and a PR, never a repo's main checkout.

### Rule scope

| Scope | File | Example |
| --- | --- | --- |
| One repository | `<repo>/AGENTS.md` | "Read the drizzle migration before editing an Ent schema." |
| One workspace (several repos) | Workspace `AGENTS.md` | "Deploy backend before the dashboard change that depends on it." |
| Every project you work on | Global rules: `~/AGENTS.md`, loaded through `~/.claude/CLAUDE.md` (`@~/AGENTS.md`) and `~/.codex/AGENTS.md` | "Work in a worktree; never edit the main checkout." |

Start at the narrowest scope. Move a rule up one scope when the same lesson shows up in a second repository or workspace.

## Steps

### 1. Classify the outcome (always)

Answer in two or three lines, for yourself:

- What was the task, and did it succeed on the first try?
- What went wrong, or took longer than it should? Count user corrections, failed CI runs, review rounds, reverted commits, wrong assumptions.
- Root cause in one sentence. Ask "why" until you reach something a rule, a test, or a tool could have prevented. "I was careless" is not a root cause; "I edited the schema from memory instead of reading the migration" is.

If nothing went wrong and you learned nothing new, stop here.

### 2. Check the ledger

Re-read `agent-docs/ledger.md` right before you edit it; other sessions write to it too. Look for an existing row with the same root cause, even if the symptom differs.

- Match: increment `Count`, update `Last seen`, append the new evidence.
- No match: add a row with `Count` 1 and the next free ID (`L-NNNN`).

Also log successes that saved real time ("ran the tests locally before pushing and skipped a CI round trip") with type `method`. Methods are promoted the same way as mistakes.

### 3. Turn the failure into artifacts

Produce only what the failure warrants:

- **Tests.** Write a test that fails before the fix and passes after. Prefer a unit test; add an integration test when the bug lived in a seam between components (DB mapping, resolver ↔ service, API contract, auth). Name the test after the behaviour, not the ticket. Run it.
- **ADR.** Only when you made or reversed a design decision. Link the ADR it supersedes.
- **Postmortem.** Blameless. Timeline, impact, root cause, why it was not caught earlier, action items (test, rule, tool, or a decision for the user).
- **Shared lesson.** If the knowledge applies beyond this repo, add it to a topic file in `agent-docs/lessons/` and list that file in `agent-docs/README.md`. Extend an existing topic file before creating a new one.

### 4. Promote to a rule

Promote when either holds:

- A `mistake` row reaches `Count` ≥ 2.
- A `method` row has saved time at least twice, or the user stated it as a standing rule.

How to write the rule:

- One imperative sentence, plus a short reason if it is not self-evident. Put it in the section an agent reads when it is about to make that mistake.
- Make it checkable: "Run `make test` before pushing", not "Be careful with tests".
- Do not duplicate. If a rule already covered it and the mistake happened anyway, the rule is unclear or in the wrong place: rewrite or move it instead of adding another.
- If a test, lint, or CI check can enforce it, add that check and mention it in the rule.
- Set the ledger row's `Status` to `promoted → <file>#<section>`.

Rule files load into every session, so keep each one under about 150 lines. Before adding to a file at that size, merge overlapping rules and delete rules whose subject no longer exists.

### 5. Report

End your final message with one short line, for example:
`RSI: L-0004 count 2 → promoted to backend/AGENTS.md#Shared Schema; regression test in internal/admin/user_test.go.`
If nothing was recorded, say nothing about RSI.

## Do not

- Do not write a postmortem for a slip you caught yourself before committing.
- Do not record secrets, tokens, customer data, or email addresses in any document.
- Do not edit a repo's main checkout to add a test, ADR, or rule.
- Do not let the retrospective delay delivery. Open the PR first and do the retrospective while CI runs.
