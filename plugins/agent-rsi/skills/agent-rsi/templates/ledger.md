# Agent ledger

Every recorded mistake (`mistake`), measured time sink (`slow`), and method that saved time (`method`). Maintained by the `agent-rsi` skill.

- Re-read this file right before you edit it; other sessions write to it too.
- Same root cause → increment `Count` on the existing row; do not add a new row.
- `Count` ≥ 2 → promote to a rule file and set `Status` to `promoted → <file>#<section>`. A scheduled sweep sets `proposed → <file>#<section>` instead and leaves the rule file to a reviewed change.

| ID | Type | Root cause / method | Count | Last seen | Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
