# skills

[English](README.md) | 中文

[@luoling8192](https://github.com/luoling8192) 的 agent skills 合集。支持 Claude Code、Codex、Cursor，以及 [skills.sh](https://skills.sh) 支持的其他 agent。

## Skill 列表

| Skill | 用途 | 来源 |
| --- | --- | --- |
| [`agent-rsi`](plugins/agent-rsi/skills/agent-rsi/SKILL.md) | 每次任务后复盘：记录错误和有效方法的次数，生成回归测试、ADR、postmortem，同一问题出现两次就写进 `AGENTS.md` | 本仓库 |
| [`software-design-philosophy`](skills/software-design-philosophy/SKILL.md) | 基于《A Philosophy of Software Design》的设计审查：深模块、信息隐藏、复杂度 | [software-design-philosophy-skill](https://github.com/luoling8192/software-design-philosophy-skill) |
| [`technical-writing`](skills/technical-writing/SKILL.md) | 中文内部技术写作：设计文档、评审稿、postmortem、分享稿 | [technical-writing](https://github.com/luoling8192/technical-writing) |
| [`ai-coding-discipline`](skills/ai-coding-discipline/SKILL.md) | 约束 AI 写代码时的常见反模式 | [ai-coding-principles](https://github.com/luoling8192/ai-coding-principles) |
| [`ddia-principles`](skills/ddia-principles/SKILL.md) | 基于《Designing Data-Intensive Applications》的数据系统设计 | [ai-coding-principles](https://github.com/luoling8192/ai-coding-principles) |
| [`create-pr-with-evidence`](skills/create-pr-with-evidence/SKILL.md) | 带可验证上下文、架构证据和前后对比截图的 PR | [create-pr-with-evidence-skill](https://github.com/luoling8192/create-pr-with-evidence-skill) |

## 安装

安装全部 skill，自动检测本机的 agent：

```bash
npx skills add luoling8192/skills
```

只装一个，全局安装到指定 agent：

```bash
npx skills add luoling8192/skills --skill agent-rsi --global --agent claude-code --agent codex
```

只看列表，不安装：

```bash
npx skills add luoling8192/skills --list
```

之后用 `npx skills update` 更新。

### 带 Stop hook 的 agent-rsi（Claude Code）

`npx skills add` 只安装 skill 文件，agent 自己判断什么时候运行 `agent-rsi`。如果想让 Claude Code 在每次改文件、提交、开 PR 或部署之后自动要求复盘，安装 plugin，它会加一个 Stop hook：

```
/plugin marketplace add luoling8192/skills
/plugin install agent-rsi@luoling8192-skills
```

hook 需要 `python3`。只读的轮次直接放过；同一段新工作只会提醒一次。

不支持 hook 的 agent，在全局规则文件（`~/AGENTS.md`、`~/.codex/AGENTS.md` 或 `~/.claude/CLAUDE.md`）里加一行：

```markdown
- After any task that changed code, config, pull requests, or deployments, run the `agent-rsi` skill.
```

## agent-rsi 怎么工作

1. 任务结束后，agent 判断结果，找出出错的根因。
2. 根因记进工作区根目录的 `agent-docs/ledger.md`。同一根因再次出现时，给原来那行加次数，不新增一行。
3. 出错会生成回归测试，需要时再写 ADR、postmortem，或者在 `agent-docs/lessons/` 里写共享经验。
4. 次数到 2 时，写成规则，放进覆盖范围最小的那个 `AGENTS.md`：仓库级、工作区级，或全局的 `~/AGENTS.md`。

Skill 按需加载，规则每次会话都加载。所以 `agent-rsi` 本身是 skill，它写出来的规则放在 `AGENTS.md`。

## 仓库结构

```
skills/              从来源仓库同步，不要在这里改
plugins/agent-rsi/   agent-rsi skill 和 Claude Code plugin（Stop hook），在本仓库维护
sources.json         每个同步 skill 的来源仓库和路径
scripts/sync.py      把来源复制到 skills/
```

[同步 workflow](.github/workflows/sync.yml) 每天从来源仓库同步一次 `skills/`，也可以在 Actions 页手动运行。要改同步来的 skill，去来源仓库提 PR；本仓库里改动 `skills/` 的 PR 会被 CI 拦下。

要加入别的仓库的 skill，在 `sources.json` 里加一项，然后运行 `python3 scripts/sync.py`。

## License

MIT。每个同步来的 skill 保留来源仓库的 `LICENSE`。
