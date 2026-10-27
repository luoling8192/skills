#!/usr/bin/env python3
"""Claude Code Stop hook: ask for an agent-rsi retrospective after real work.

Blocks the stop once when the transcript has new file edits, commits, PRs, or
deploys since the last retrospective prompt. Read-only turns pass through.
"""
import json
import os
import sys

WRITE_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
BASH_MARKERS = ("git commit", "git push", "gh pr create", "gh pr merge", "deploy", "wrangler")
STATE_DIR = os.path.join(os.environ.get("TMPDIR", "/tmp"), "agent-rsi")


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

    if not has_work(lines[offset:]):
        return

    print(json.dumps({
        "decision": "block",
        "reason": (
            "Before stopping, run the agent-rsi skill on the work since the last retrospective. "
            "If the task went cleanly and taught nothing new, stop without comment."
        ),
    }))


if __name__ == "__main__":
    main()
