# skills

Public collection of agent skills, installable with `npx skills add luoling8192/skills`.

- `skills/*` is synced from the repositories in `sources.json` and overwritten on every sync. Never edit it here; change the source repository.
- `plugins/agent-rsi/` is maintained here. Keep its skill and its hook generic: no project names, private paths, or internal URLs.
- `SKILL.md` frontmatter holds only `name` and `description`. Skill names must be unique across the repository; the skills CLI installs only the first skill with a given name.
- When you add, remove, or rename a skill, update the tables in both `README.md` and `README.zh-CN.md`.
- Before you push, run `npx skills add . --list` and confirm every skill is listed.
