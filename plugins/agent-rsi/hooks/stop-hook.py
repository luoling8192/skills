#!/usr/bin/env python3
"""Claude Code Stop hook: ask for an agent-rsi retrospective after real work.

Blocks the stop once when the transcript has new file edits, commits, PRs, or
deploys since the last retrospective prompt, or when the new turns wasted
measurable time. Other read-only turns pass through. The prompt quotes the
top findings of scripts/session-stats.py for the new turns.
"""
import importlib.util
import json
import os
import sys

WRITE_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
BASH_MARKERS = ("git commit", "git push", "gh pr create", "gh pr merge", "deploy", "wrangler")
STATE_DIR = os.path.join(os.environ.get("TMPDIR", "/tmp"), "agent-rsi")
STATS_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "agent-rsi", "scripts", "session-stats.py")
# A read-only stretch asks for a retrospective only when its tool time reaches this many seconds.
READ_ONLY_MIN_SECONDS = 900
FINDINGS_SHOWN = 3


def session_findings(transcript, lines):
    """Return (tool seconds, findings) for the new lines. Never raise: the hook must not break a stop."""
    try:
        spec = importlib.util.spec_from_file_location("agent_rsi_session_stats", STATS_SCRIPT)
        stats = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stats)
        _, calls, _, _ = stats.read_lines(transcript, lines)
        if not calls:
            return 0, []
        report = stats.analyse(calls)
        return report["tool_seconds"], report["findings"]
    except Exception:
        return 0, []


def has_work(lines):
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        content = (entry.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = block.get("name")
            if name in WRITE_TOOLS:
                return True
            if name == "Bash":
                command = str((block.get("input") or {}).get("command", ""))
                if any(marker in command for marker in BASH_MARKERS):
                    return True
    return False


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return
    if payload.get("stop_hook_active"):
        return
    transcript = payload.get("transcript_path")
    session = payload.get("session_id") or "unknown"
    if not transcript or not os.path.exists(transcript):
        return

    os.makedirs(STATE_DIR, exist_ok=True)
    state_file = os.path.join(STATE_DIR, session)
    offset = 0
    if os.path.exists(state_file):
        try:
            offset = int(open(state_file).read().strip() or 0)
        except ValueError:
            offset = 0

    with open(transcript, encoding="utf-8", errors="replace") as handle:
        lines = handle.readlines()
    with open(state_file, "w") as handle:
        handle.write(str(len(lines)))

    new_lines = lines[offset:]
    worked = has_work(new_lines)
    seconds, findings = session_findings(transcript, new_lines)
    if not worked and not (findings and seconds >= READ_ONLY_MIN_SECONDS):
        return

    reason = (
        "Before stopping, run the agent-rsi skill on the work since the last retrospective. "
        "If the task went cleanly and taught nothing new, stop without comment."
    )
    if findings:
        reason += " session-stats.py found: " + " ".join(findings[:FINDINGS_SHOWN])
    print(json.dumps({"decision": "block", "reason": reason}))


if __name__ == "__main__":
    main()
