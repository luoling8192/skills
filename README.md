# skills

English | [中文](README.zh-CN.md)

Agent skills by [@luoling8192](https://github.com/luoling8192), in one repository. Works with Claude Code, Codex, Cursor, and every other agent [skills.sh](https://skills.sh) supports.

## Skills

| Skill | Use it for | Source |
| --- | --- | --- |
| [`agent-rsi`](plugins/agent-rsi/skills/agent-rsi/SKILL.md) | Retrospective after every task: counts mistakes and proven methods, writes regression tests, ADRs, and postmortems, and promotes anything seen twice into `AGENTS.md` | this repository |
| [`software-design-philosophy`](skills/software-design-philosophy/SKILL.md) | Design review based on *A Philosophy of Software Design*: deep modules, information hiding, complexity | [software-design-philosophy-skill](https://github.com/luoling8192/software-design-philosophy-skill) |
| [`technical-writing`](skills/technical-writing/SKILL.md) | Chinese internal technical writing: design docs, review notes, postmortems, sharing posts | [technical-writing](https://github.com/luoling8192/technical-writing) |
| [`ai-coding-discipline`](skills/ai-coding-discipline/SKILL.md) | Coding discipline that prevents common AI coding anti-patterns | [ai-coding-principles](https://github.com/luoling8192/ai-coding-principles) |
| [`ddia-principles`](skills/ddia-principles/SKILL.md) | Data system design based on *Designing Data-Intensive Applications* | [ai-coding-principles](https://github.com/luoling8192/ai-coding-principles) |
| [`create-pr-with-evidence`](skills/create-pr-with-evidence/SKILL.md) | Pull requests with verifiable change context, architecture evidence, and before/after screenshots | [create-pr-with-evidence-skill](https://github.com/luoling8192/create-pr-with-evidence-skill) |

## Install

All skills, for the agents detected on your machine:

```bash
npx skills add luoling8192/skills
```

One skill, globally, for specific agents:

```bash
npx skills add luoling8192/skills --skill agent-rsi --global --agent claude-code --agent codex
```

List without installing:

```bash
npx skills add luoling8192/skills --list
```

Update later with `npx skills update`.

### agent-rsi with its Stop hook (Claude Code)

`npx skills add` installs skill files only, so the agent runs `agent-rsi` when it decides to. To have Claude Code ask for a retrospective automatically after every task that edited files, committed, opened a pull request, or deployed, install the plugin, which adds a Stop hook:

```
/plugin marketplace add luoling8192/skills
/plugin install agent-rsi@luoling8192-skills
```

The hook needs `python3`. Read-only turns pass through, and it asks at most once per stretch of new work.

For agents without hooks, add a line to your global rules file (`~/AGENTS.md`, `~/.codex/AGENTS.md`, or `~/.claude/CLAUDE.md`):

```markdown
- After any task that changed code, config, pull requests, or deployments, run the `agent-rsi` skill.
```

## How agent-rsi works

1. After a task, the agent classifies the outcome and finds the root cause of anything that went wrong.
2. It logs the root cause in `agent-docs/ledger.md` at the workspace root. A repeat of the same root cause increments the existing row's count instead of adding a new row.
3. A failure produces a regression test and, where warranted, an ADR, a postmortem, or a shared lesson in `agent-docs/lessons/`.
4. When a count reaches 2, the lesson becomes a rule in the narrowest `AGENTS.md` that covers it: a repository's, a workspace's, or your global `~/AGENTS.md`.

Skills are loaded on demand; rules are loaded every session. That is why `agent-rsi` is a skill, while the rules it writes go into `AGENTS.md`.

## Repository layout

```
skills/              synced from the source repositories; do not edit here
plugins/agent-rsi/   agent-rsi skill and Claude Code plugin (Stop hook); maintained here
sources.json         which source repository and path each synced skill comes from
scripts/sync.py      copies the sources into skills/
```

A [workflow](.github/workflows/sync.yml) syncs `skills/` from the source repositories every day, and you can run it by hand from the Actions tab. To change a synced skill, open a pull request against its source repository; pull requests here that touch `skills/` fail CI.

To add a skill from another repository, add an entry to `sources.json` and run `python3 scripts/sync.py`.

## License

MIT. Each synced skill keeps its source repository's `LICENSE`.
