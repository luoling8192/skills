---
name: agent-rsi
description: >
  Agent retrospective and self-improvement loop. Run at the end of any task that changed code, docs, config, pull requests, or deployments, and whenever a task failed, was redone, or the user corrected you. Records what worked and what failed, turns each failure into regression tests, an ADR, and a postmortem, counts repeated mistakes in agent-docs/ledger.md, and promotes repeated mistakes and proven methods into the right AGENTS.md. Triggers: "复盘", "总结经验", "postmortem", "retro", "RSI", "沉淀", or a Stop hook asking for a retrospective.
---

# Agent RSI (retrospective → self-improvement)

Goal: each mistake happens at most twice. The first time it is recorded. The second time it becomes a rule that every agent loads.

Keep it small. A retrospective that takes longer than the task is waste. For a clean, routine task, step 1 is enough.

## Where things go

The **workspace** is the directory the session started in: the one holding the top-level `AGENTS.md` for this work. Its `agent-docs/` directory holds the ledger and shared lessons. The **machine** directory `~/agent-docs/` has the same layout and holds what every project on this host needs. If either directory does not exist when you need it, create it from `templates/agent-docs-README.md` and `templates/ledger.md`.

### Lesson scope

Store each lesson where every session that needs it will read it:

| Lesson about | Location |
| --- | --- |
| One repository | That repository's docs or `AGENTS.md` |
| One workspace (several repos) | `<workspace>/agent-docs/lessons/<topic>.md` |
| Tools on this machine, a cluster or third-party service, or the user's preferences | `~/agent-docs/lessons/<topic>.md`, with a pointer in the global rules |

- Do not store a lesson only in an agent's per-directory memory, such as Claude Code project memory. Sessions that start in another directory never see it.
- Before you add to a workspace lesson, ask whether a session in another project needs it too. If it does, it belongs in `~/agent-docs/`.
- When you find a lesson at too narrow a scope, move it, and leave a one-line pointer in the old file.

| Artifact | Location | When |
| --- | --- | --- |
| Regression unit / integration test | The affected repo, next to the code, in the same PR as the fix | Every bug that reached a commit, review, CI, or production |
| ADR | `<repo>/docs/adr/NNNN-<slug>.md` | A design choice that someone would later question or undo |
| Postmortem | `<repo>/docs/postmortems/YYYY-MM-DD-<slug>.md` if repo-specific; `agent-docs/postmortems/` if cross-repo or about agent process | Failure that reached CI, a reviewer, the user, or production; or cost more than ~30 min |
| Shared lesson | See "Lesson scope" | Knowledge another agent in another repo would also need |
| Counter | `agent-docs/ledger.md` of the same scope as the lesson | Every failure, and every proven method |
| Rule | See "Rule scope" below | Ledger count reaches 2, or a method proved itself twice |

Templates are in `templates/` next to this file. `scripts/session-stats.py` measures where session time went (see step 1). Repo files (tests, ADRs, repo postmortems, repo `AGENTS.md`) go through the task's branch and a PR, never a repo's main checkout.

### Rule scope

| Scope | File | Example |
| --- | --- | --- |
| One repository | `<repo>/AGENTS.md` | "Read the drizzle migration before editing an Ent schema." |
| One workspace (several repos) | Workspace `AGENTS.md` | "Deploy backend before the dashboard change that depends on it." |
| Every project you work on | Global rules: `~/AGENTS.md`, loaded through `~/.claude/CLAUDE.md` (`@~/AGENTS.md`) and `~/.codex/AGENTS.md` | "Work in a worktree; never edit the main checkout." |

Start at the narrowest scope. Move a rule up one scope when the same lesson shows up in a second repository or workspace.

Put rules in these `AGENTS.md` files, never in a skill. A skill loads only when its description matches the task, but a rule must be in context before the mistake happens. A rule can point to a lesson file for the details.

## Steps

### 1. Classify the outcome (always)

First measure the session. Do not rely on memory for what was slow:

```sh
python3 -I <this skill>/scripts/session-stats.py --transcript <current transcript>
```

Claude Code transcripts are `~/.claude/projects/<cwd with / as ->/<session id>.jsonl`. Codex transcripts are under `~/.codex/sessions/`. With no `--transcript`, the script reads every transcript; add `--since 1d` to limit it.

The script pairs each tool call with its result and prints findings: command families that take a large share of time, calls that are never fast, slow calls, repeated commands, failures, polling loops, and denied calls. Treat each finding as a candidate `slow` or `mistake` row for step 2. A finding is evidence, not a root cause. Read the command and its output before you name a cause.

Limits of the numbers:

- Times include permission checks and user approval.
- Background calls and calls sent in one parallel batch have no time of their own.
- The report shows command text. Copy conclusions into the ledger, never raw commands, hosts, or paths.

Then answer in two or three lines, for yourself:

- What was the task, and did it succeed on the first try?
- What went wrong, or took longer than it should? Count user corrections, failed CI runs, review rounds, reverted commits, wrong assumptions.
- Root cause in one sentence. Ask "why" until you reach something a rule, a test, or a tool could have prevented. "I was careless" is not a root cause; "I edited the schema from memory instead of reading the migration" is.

If nothing went wrong and you learned nothing new, stop here.

### 2. Check the ledger

Re-read `agent-docs/ledger.md` right before you edit it; other sessions write to it too. Look for an existing row with the same root cause, even if the symptom differs.

- Match: increment `Count`, update `Last seen`, append the new evidence.
- No match: add a row with `Count` 1 and the next free ID (`L-NNNN`).

Log a time sink found in step 1 with type `slow`, for example "each remote exec pays 10 s of connection setup". Put the measured numbers in `Evidence`.

Also log successes that saved real time ("ran the tests locally before pushing and skipped a CI round trip") with type `method`. Methods are promoted the same way as mistakes.

Then score the rules that shaped this task. Only score rules you acted on; do not audit every loaded rule.

- A promoted rule changed what you did and saved a step or a mistake: add 1 to `Helped` and set `Last applied` to today.
- A rule sent you the wrong way: it named a file, command, version, host, or limit that is no longer true; it disagreed with the code; or the user corrected you because you followed it. Add 1 to `Misled`, put what was wrong in `Evidence`, and fix or retire the rule now (see "Retire stale rules").
- If the rule has no ledger row, add one of type `method` with `Count` 2 and `Status` `promoted → <file>#<section>`, then score it.
- Rows written before these columns existed have fewer cells. Fill the missing cells when you score the row; an empty cell counts as 0 or never.

### 3. Turn the failure into artifacts

Produce only what the failure warrants:

- **Tests.** Write a test that fails before the fix and passes after. Prefer a unit test; add an integration test when the bug lived in a seam between components (DB mapping, resolver ↔ service, API contract, auth). Name the test after the behaviour, not the ticket. Run it.
- **ADR.** Only when you made or reversed a design decision. Link the ADR it supersedes.
- **Postmortem.** Blameless. Timeline, impact, root cause, why it was not caught earlier, action items (test, rule, tool, or a decision for the user).
- **Shared lesson.** If the knowledge applies beyond this repo, add it to a topic file in `agent-docs/lessons/` and list that file in `agent-docs/README.md`. Extend an existing topic file before creating a new one.

### 4. Promote to a rule

Promote when either holds:

- A `mistake` or `slow` row reaches `Count` ≥ 2.
- A `method` row has saved time at least twice, or the user stated it as a standing rule.

How to write the rule:

- One imperative sentence, plus a short reason if it is not self-evident. Put it in the section an agent reads when it is about to make that mistake.
- Make it checkable: "Run `make test` before pushing", not "Be careful with tests".
- Do not duplicate. If a rule already covered it and the mistake happened anyway, the rule is unclear or in the wrong place: rewrite or move it instead of adding another.
- If a test, lint, or CI check can enforce it, add that check and mention it in the rule.
- When a rule states a fact about the environment rather than a way of working (a host, cluster, version, release bug, service limit, quota, or network condition), end it with `(verified YYYY-MM-DD)`. When the fact has a known end, add the condition: `(verified 2026-03-02; until tool > 1.4.0)`. A session that observes the fact again updates the date.
- Set the ledger row's `Status` to `promoted → <file>#<section>`.

Rule files load into every session, so keep each one under about 150 lines. Before adding to a file at that size, run "Retire stale rules" on it and merge overlapping rules.

### Retire stale rules

A rule that is no longer true costs more than a missing rule: agents follow a rule file even when the code in front of them disagrees. Retire a rule when any of these holds:

| Signal | Action |
| --- | --- |
| `Misled` ≥ 2, or `Misled` ≥ 1 and `Misled` ≥ `Helped` | Rewrite the rule so it would not have misled, or retire it |
| Its `until` condition is met (the release shipped, the issue closed, the host is gone) | Retire it, or reduce it to what is still true |
| A file, command, flag, skill, or host it names no longer exists | Fix the reference, or retire it if its subject is gone |
| An environment fact is more than 30 days past `verified` | Check it with one command; update the date or the fact |
| A newer rule or user statement contradicts it | Keep the newer one; retire the older |
| No `Last applied` or `Last seen` in the last 60 days | Propose moving it to a lesson file; it stays findable but stops loading in every session |

- Check the signal before you act: read the issue, run the command, open the file. A stale-looking rule can be a guard that simply never fired.
- Remove the rule text from the rule file. Do not leave "obsolete" notes there; rule files load into every session.
- Keep the ledger row and record why: `Status` becomes `retired YYYY-MM-DD: <reason>`, `superseded → L-NNNN`, or `demoted → <lesson file>`. A later session that meets the same problem finds the history there.
- When you move a rule to a lesson file, list that file in `agent-docs/README.md`.

### Sweep across sessions

A cost that is small in each session can be large in total. Run a sweep on a schedule, for example weekly, or when the user asks:

1. Run `session-stats.py --since 7d`. Add `--json` to read the numbers in a script.
2. For each finding, look for a ledger row with the same root cause. On a match, increment `Count` once per sweep, not once per session. Otherwise add a row.
3. A sweep runs without the user. It does not edit rule files. For each row that reaches the promotion threshold, write the proposed rule and set `Status` to `proposed → <file>#<section>`. Put the change in a pull request where the rule file is in a repository; otherwise list it for the user.
4. Check each rule file in scope against "Retire stale rules": the ledger counters, every `until` condition, every `verified` date older than 30 days, and the names each rule references. Verify each signal with one command or read. Propose each retirement, rewrite, or move the same way as a new rule, with its evidence, and set the row's `Status` to `proposed retire → <reason>`. Do not edit the rule file.
5. Report the top findings, the ledger changes, the proposed rules, and the proposed retirements in one short message.

### 5. Report

End your final message with one short line, for example:
`RSI: L-0004 count 2 → promoted to backend/AGENTS.md#Shared Schema; regression test in internal/admin/user_test.go.`
If nothing was recorded, say nothing about RSI.

## Do not

- Do not write a postmortem for a slip you caught yourself before committing.
- Do not record secrets, tokens, customer data, or email addresses in any document.
- Do not edit a repo's main checkout to add a test, ADR, or rule.
- Do not let the retrospective delay delivery. Open the PR first and do the retrospective while CI runs.
