# Agent ledger

Every recorded mistake (`mistake`), measured time sink (`slow`), and method that saved time (`method`). Maintained by the `agent-rsi` skill.

- Re-read this file right before you edit it; other sessions write to it too.
- Same root cause → increment `Count` on the existing row; do not add a new row.
- `Count` ≥ 2 → promote to a rule file and set `Status` to `promoted → <file>#<section>`. A scheduled sweep sets `proposed → <file>#<section>` instead and leaves the rule file to a reviewed change.
- `Helped` / `Misled` count how often a promoted rule saved a step or sent an agent the wrong way; `Last applied` is the last day it helped. An empty cell counts as 0 or never.
- A retired rule keeps its row: `Status` becomes `retired YYYY-MM-DD: <reason>`, `superseded → L-NNNN`, or `demoted → <lesson file>`.

| ID | Type | Root cause / method | Count | Last seen | Evidence | Status | Helped | Misled | Last applied |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
