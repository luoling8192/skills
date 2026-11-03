#!/usr/bin/env python3
"""Measure where agent session time went, from Claude Code and Codex transcripts.

Reads JSONL transcripts, pairs every tool call with its result, and reports:
time per command family, the slowest calls, failures, repeated commands,
polling loops, and denied calls. Prints findings that cross fixed thresholds.

Standard library only. Reads local files and sends nothing anywhere.

Examples:
  session-stats.py --transcript ~/.claude/projects/<dir>/<session>.jsonl
  session-stats.py --since 7d                # every transcript changed in 7 days
  session-stats.py --since 7d --json         # machine-readable
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import shlex
import statistics
import sys
from collections import Counter, defaultdict

DEFAULT_ROOTS = ("~/.claude/projects", "~/.codex/sessions")

# Thresholds for findings. Durations are seconds.
SLOW_CALL = 300
FAMILY_SHARE = 0.20
FAMILY_MIN_TOTAL = 300
# A quarter of a family's calls took at least this long.
OVERHEAD_QUARTILE = 5
OVERHEAD_MIN_CALLS = 5
REPEAT_MIN = 3
FAILURE_MIN = 3
FAILURE_RATE = 0.25
# Programs whose non-zero exit is usually an answer, not a failure.
FAILURE_NOISE = {"grep", "rg", "diff", "cmp", "test", "[", "pgrep", "pkill", "which", "command"}
POLL_MIN_TOTAL = 300
SLOW_FAMILIES_SHOWN = 8
REPEATED_MIN_TOTAL = 300
REPEATED_SHOWN = 5

BACKGROUND_MARKERS = (
    "Command running in background",
    "You will be notified when it completes",
)
DENIAL_MARKERS = (
    "The user doesn't want to proceed",
    "tool use was rejected",
    "Permission to use",
)
ERROR_RE = re.compile(r"Exit code [1-9]\d*|exited with (?:code|status) [1-9]\d*|Process exited with code [1-9]")
POLL_RE = re.compile(r"\b(until|while)\b[^\n]*;\s*do\b[^\n]*\bsleep\b|\bsleep\s+\d+\s*;\s*done", re.S)
# Wrappers and shell words that are not the program that does the work.
SKIP_PROGRAMS = {"timeout", "time", "nice", "nohup", "env", "sudo", "exec", "command", "export", "set", "then", "do", "else", "elif", "if", "until", "while", "!", "{", "("}
# Words whose next argument is skipped too.
SKIP_WITH_ARGUMENT = {"cd", "source", ".", "pushd"}
# Segments that start with these words hold no command of their own.
SKIP_SEGMENTS = {"for", "select", "case", "function", "local", "return", "exit", "break", "continue"}
TRIVIAL_PROGRAMS = {"echo", "printf", "true", "false", "mkdir", "sleep", "cat", "rm", "ls", "test", "[", "[[", "done", "fi", "esac", "}", ")", "wait", "date", "read", "trap", "kill"}
# Flags that take a separate value in common CLIs, so the value is not a subcommand.
VALUE_FLAGS = {"-n", "--namespace", "-F", "--filter", "-C", "--context", "--kubeconfig", "-R", "--repo", "-c", "-o", "--cwd", "-w", "--workspace"}
# A third word is part of the family only when it is a common verb, so names and paths stay out.
THIRD_WORDS = {"add", "apply", "build", "checks", "create", "delete", "describe", "diff", "edit", "get", "install", "list", "logs", "merge", "mount", "remove", "run", "show", "status", "sync", "test", "update", "view", "watch"}
# Package runners whose third word is the tool they run, for example `pnpm exec vitest`.
RUNNERS = {"pnpm", "npm", "npx", "yarn", "bun", "bunx", "uv", "uvx", "poetry"}
RUNNER_VERBS = {"exec", "dlx", "x", "run"}
# Quick helpers. A command that chains one of these with heavier work is named after the heavier work.
LIGHT_FAMILIES = {
    "awk", "basename", "chmod", "cp", "cut", "dirname", "find", "grep", "head", "jq", "ln", "mv", "realpath", "rg",
    "sed", "seq", "sort", "tail", "tee", "touch", "tr", "uniq", "wc", "xargs", "base64", "split", "stat", "du", "df",
    "git add", "git branch", "git diff", "git log", "git merge-base", "git rev-parse", "git show", "git status",
}
# Lines of inline Python or JavaScript that leak out of a quoted multi-line argument.
CODE_WORDS = {"import", "from", "const", "let", "var", "def", "return", "print", "await", "class", "async", "function"}
PROGRAM_RE = re.compile(r"^[A-Za-z_.~/][\w.~/+-]*$")
HEREDOC_RE = re.compile(r"<<-?\s*(['\"]?)(\w+)\1")
ASSIGNMENT_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", re.S)
SUBCOMMAND_RE = re.compile(r"^[a-z][a-z0-9-]*$")
REDACTIONS = (
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "<email>"),
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "<ip>"),
    (re.compile(r"(https?|wss?|socks5h?)://[^\s/'\"]+"), r"\1://<host>"),
    (re.compile(r"\b[A-Za-z0-9_\-]{32,}\b"), "<token>"),
    (re.compile(r"/(home|Users)/[^/\s]+"), r"/\1/user"),
)


def parse_time(value):
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def redact(text):
    for pattern, replacement in REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(text_of(part.get("text", part.get("content", "")) if isinstance(part, dict) else part) for part in content)
    if isinstance(content, dict):
        return text_of(content.get("text") or content.get("content") or content.get("output") or "")
    return "" if content is None else str(content)


def split_words(text):
    try:
        return shlex.split(text, comments=True)
    except ValueError:
        return text.split()


def strip_heredocs(command):
    """Drop the bodies of heredocs, which hold data or scripts, not shell commands."""
    lines = []
    terminator = None
    for line in command.split("\n"):
        if terminator:
            if line.strip() == terminator:
                terminator = None
            continue
        match = HEREDOC_RE.search(line)
        if match:
            terminator = match.group(2)
        lines.append(line)
    return "\n".join(lines)


def command_family(tool, command):
    """Name the program and its subcommands, for example `git commit` or `gh pr checks`."""
    if not command:
        return tool
    text = strip_heredocs(command).replace("$(", ";").replace("`", ";")
    variables = {}
    fallback = None
    candidates = []
    for segment in re.split(r"&&|\|\||;|\||\n|\(|\)", text):
        words = split_words(segment)
        if not words or words[0] in SKIP_SEGMENTS:
            continue
        index = 0
        expansions = 0
        while index < len(words):
            word = words[index]
            assignment = ASSIGNMENT_RE.match(word)
            if assignment:
                variables[assignment.group(1)] = assignment.group(2)
                index += 1
            elif word in SKIP_PROGRAMS:
                index += 1
                if word == "timeout" and index < len(words) and re.match(r"^[\d.]+[smhd]?$", words[index]):
                    index += 1
            elif word in SKIP_WITH_ARGUMENT:
                index += 2
            elif re.fullmatch(r"\$\{?(\w+)\}?", word) and word.strip("${}") in variables and expansions < 3:
                # Expand `R="timeout 60 tool -n ns"; $R sub` so the family is `tool sub`.
                expansions += 1
                words[index:index + 1] = split_words(variables[word.strip("${}")]) or [""]
            else:
                break
        if index >= len(words):
            continue
        word = words[index]
        program = os.path.basename(word)
        if (program.startswith("-") or word.startswith("/dev/") or re.match(r"^\d*[<>&]", word)
                or not PROGRAM_RE.match(program) or program in SKIP_SEGMENTS or program in CODE_WORDS):
            continue
        if program in TRIVIAL_PROGRAMS:
            fallback = fallback or program
            continue
        parts = [program]
        skip_next = False
        for word in words[index + 1:]:
            if skip_next:
                skip_next = False
                continue
            if word.startswith("-"):
                skip_next = word in VALUE_FLAGS
                continue
            if not SUBCOMMAND_RE.match(word):
                break
            if len(parts) == 2 and not (word in THIRD_WORDS or (program in RUNNERS and parts[1] in RUNNER_VERBS)):
                break
            parts.append(word)
            if len(parts) == 3:
                break
        if program.startswith("python") and len(words) > index + 1 and words[index + 1] in ("-", "-c", "-I"):
            parts = [program, "inline"]
        candidates.append(" ".join(parts))
    for family in candidates:
        if family not in LIGHT_FAMILIES and family.split()[0] not in LIGHT_FAMILIES and family != "python3 inline":
            return family
    return candidates[0] if candidates else (fallback or tool)


class Call:
    __slots__ = ("session", "tool", "command", "family", "start", "end", "output", "error", "background", "denied", "batch")

    def __init__(self, session, tool, command, start):
        self.session = session
        self.tool = tool
        self.command = command
        self.family = command_family(tool, command) if tool in ("Bash", "exec_command", "shell", "exec") else tool
        self.start = start
        self.end = None
        self.output = ""
        self.error = False
        self.background = False
        self.denied = False
        # Size of the parallel batch the call was sent in. Claude Code writes the
        # results of one batch together, so a batched call's time is the batch's time.
        self.batch = 1

    @property
    def seconds(self):
        if not self.start or not self.end:
            return 0.0
        return max(0.0, (self.end - self.start).total_seconds())


JS_COMMAND_RE = re.compile(r'\bcmd\s*:\s*("(?:[^"\\]|\\.)*")')


def tool_command(name, arguments):
    if isinstance(arguments, str) and "exec_command" in arguments:
        # Codex `exec` runs JavaScript that calls `tools.exec_command({cmd: "..."})`.
        match = JS_COMMAND_RE.search(arguments)
        if match:
            try:
                return json.loads(match.group(1))
            except ValueError:
                return match.group(1)[1:-1]
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except ValueError:
            return arguments
    if isinstance(arguments, dict):
        for key in ("command", "cmd", "input"):
            value = arguments.get(key)
            if isinstance(value, list):
                return " ".join(map(str, value))
            if isinstance(value, str):
                return value
    return ""


def read_transcript(path):
    """Return (session id, calls, first timestamp, last timestamp) for one JSONL transcript."""
    with open(path, encoding="utf-8", errors="replace") as handle:
        return read_lines(path, handle)


def read_lines(path, lines):
    """Parse transcript lines. `path` only names the session."""
    session = os.path.splitext(os.path.basename(path))[0]
    # Codex names files `rollout-<time>-<uuid>`. Keep the UUID so short IDs stay distinct.
    uuid = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", session)
    if uuid:
        session = uuid.group(0)
    pending = {}
    batches = defaultdict(list)
    calls = []
    first = last = None
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict):
            continue
        stamp = parse_time(entry.get("timestamp"))
        if stamp:
            first = first or stamp
            last = stamp
        # Claude Code: tool_use and tool_result blocks inside message.content.
        message = entry.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    name = block.get("name", "?")
                    call = Call(session, name, tool_command(name, block.get("input")), stamp)
                    if (block.get("input") or {}).get("run_in_background"):
                        call.background = True
                    pending[block.get("id")] = call
                    batches[message.get("id") or block.get("id")].append(call)
                elif block.get("type") == "tool_result" and block.get("tool_use_id") in pending:
                    call = pending.pop(block["tool_use_id"])
                    finish(call, stamp, text_of(block.get("content")), bool(block.get("is_error")) or bool(entry.get("toolDenialKind")))
                    calls.append(call)
        # Codex: response_item payloads paired by call_id.
        payload = entry.get("payload")
        if entry.get("type") == "response_item" and isinstance(payload, dict):
            kind = payload.get("type")
            if kind in ("function_call", "custom_tool_call", "local_shell_call"):
                name = payload.get("name", kind)
                arguments = payload.get("arguments", payload.get("input", payload.get("action")))
                pending[payload.get("call_id")] = Call(session, name, tool_command(name, arguments), stamp)
            elif kind in ("function_call_output", "custom_tool_call_output", "local_shell_call_output") and payload.get("call_id") in pending:
                call = pending.pop(payload["call_id"])
                finish(call, stamp, text_of(payload.get("output")), False)
                calls.append(call)
    for batch in batches.values():
        for call in batch:
            call.batch = len(batch)
    return session, calls, first, last


def finish(call, stamp, output, error):
    call.end = stamp
    call.output = output[-2000:]
    call.background = call.background or any(marker in output for marker in BACKGROUND_MARKERS)
    call.denied = any(marker in output for marker in DENIAL_MARKERS)
    call.error = error or call.denied or bool(ERROR_RE.search(output))


def find_transcripts(roots, since):
    cutoff = (dt.datetime.now().timestamp() - since) if since else 0
    found = []
    for root in roots:
        for path in glob.glob(os.path.join(os.path.expanduser(root), "**", "*.jsonl"), recursive=True):
            if os.path.getmtime(path) >= cutoff:
                found.append(path)
    return sorted(found, key=os.path.getmtime)


def parse_duration(value):
    match = re.fullmatch(r"(\d+)([smhd])", value)
    if not match:
        raise argparse.ArgumentTypeError("use a number with s, m, h, or d, for example 7d")
    return int(match.group(1)) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[match.group(2)]


def analyse(calls):
    # A call has its own time only when it ran alone and in the foreground.
    timed_calls = [call for call in calls if not call.background and call.batch == 1]
    batched = [call for call in calls if not call.background and call.batch > 1]
    batch_seconds = {}
    for call in batched:
        key = (call.session, call.start)
        batch_seconds[key] = max(batch_seconds.get(key, 0.0), call.seconds)
    total = (sum(call.seconds for call in timed_calls) + sum(batch_seconds.values())) or 1.0

    families = defaultdict(list)
    for call in calls:
        families[call.family].append(call)
    table = []
    for family, items in families.items():
        timed = [call.seconds for call in items if not call.background and call.batch == 1]
        table.append({
            "family": family,
            "calls": len(items),
            "seconds": round(sum(timed)),
            "share": round(sum(timed) / total, 3),
            "quartile": round(sorted(timed)[len(timed) // 4], 1) if timed else 0,
            "median": round(statistics.median(timed), 1) if timed else 0,
            "max": round(max(timed)) if timed else 0,
            "failures": sum(1 for call in items if call.error),
            "untimed": len(items) - len(timed),
        })
    table.sort(key=lambda row: -row["seconds"])

    findings = []
    for row in table:
        if row["share"] >= FAMILY_SHARE and row["seconds"] >= FAMILY_MIN_TOTAL:
            findings.append(f"`{row['family']}` used {row['share']:.0%} of tool time ({row['seconds']}s in {row['calls']} calls).")
        if row["failures"] >= FAILURE_MIN and row["failures"] >= FAILURE_RATE * row["calls"] and row["family"].split()[0] not in FAILURE_NOISE:
            findings.append(f"`{row['family']}` failed {row['failures']} of {row['calls']} times.")
    # Repeated cost: calls that are never fast, times how often they ran.
    repeated = [
        row for row in table
        if row["calls"] - row["untimed"] >= OVERHEAD_MIN_CALLS and row["quartile"] >= OVERHEAD_QUARTILE
        and row["quartile"] * (row["calls"] - row["untimed"]) >= REPEATED_MIN_TOTAL
    ]
    repeated.sort(key=lambda row: -row["quartile"] * (row["calls"] - row["untimed"]))
    for row in repeated[:REPEATED_SHOWN]:
        findings.append(
            f"`{row['family']}` ran {row['calls']} times and three quarters took {row['quartile']}s or more (median {row['median']}s). "
            "Find the fixed cost per call, or make fewer calls."
        )
    slow = defaultdict(list)
    for call in timed_calls:
        if call.seconds >= SLOW_CALL:
            slow[call.family].append(call.seconds)
    for family, durations in sorted(slow.items(), key=lambda item: -sum(item[1]))[:SLOW_FAMILIES_SHOWN]:
        findings.append(f"`{family}` ran {len(durations)} calls over {SLOW_CALL}s, the longest {max(durations):.0f}s.")
    slow_batches = [seconds for seconds in batch_seconds.values() if seconds >= SLOW_CALL]
    if slow_batches:
        findings.append(f"{len(slow_batches)} parallel batches took over {SLOW_CALL}s ({sum(slow_batches):.0f}s in total). Their calls have no time of their own.")
    repeats = Counter((call.session, re.sub(r"\s+", " ", call.command.strip())) for call in calls if call.command)
    for (session, command), count in repeats.most_common():
        if count < REPEAT_MIN:
            break
        findings.append(f"The same command ran {count} times in session {session[:8]}: `{redact(command)[:100]}`.")
    polls = [call for call in timed_calls if call.command and POLL_RE.search(call.command)]
    poll_seconds = sum(call.seconds for call in polls)
    if poll_seconds >= POLL_MIN_TOTAL:
        findings.append(f"{len(polls)} polling loops (`until` or `while` with `sleep`) took {poll_seconds:.0f}s. Wait on the process or its log instead.")
    denied = [call for call in calls if call.denied]
    if denied:
        findings.append(f"{len(denied)} tool calls were denied.")
    return {
        "calls": len(calls),
        "tool_seconds": round(total),
        "background_calls": sum(1 for call in calls if call.background),
        "batched_calls": len(batched),
        "families": table,
        "slowest": [
            {"seconds": round(call.seconds), "family": call.family, "session": call.session[:8], "error": call.error, "command": redact(call.command.replace("\n", " "))[:160]}
            for call in sorted(timed_calls, key=lambda call: -call.seconds)[:15]
        ],
        "findings": findings,
    }


def print_report(report, sessions, top):
    print(f"# Session stats\n\n{len(sessions)} transcripts, {report['calls']} tool calls, {report['tool_seconds']}s of measured tool time.")
    print(f"Not timed one by one: {report['background_calls']} background calls, {report['batched_calls']} calls in parallel batches.")
    print("Times include permission checks and user approval.\n")
    print("## Findings\n")
    for finding in report["findings"] or ["None above the thresholds."]:
        print(f"- {finding}")
    print("\n## Time by command family\n")
    print("| Family | Calls | Total s | Share | 25th pct s | Median s | Max s | Failed |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in report["families"][:top]:
        print(f"| `{row['family']}` | {row['calls']} | {row['seconds']} | {row['share']:.0%} | {row['quartile']} | {row['median']} | {row['max']} | {row['failures']} |")
    print("\n## Slowest calls\n")
    for call in report["slowest"][:top]:
        mark = " (failed)" if call["error"] else ""
        print(f"- {call['seconds']}s `{call['family']}` in {call['session']}{mark}: `{call['command']}`")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--transcript", action="append", default=[], help="transcript file; repeat for more")
    parser.add_argument("--root", action="append", default=[], help=f"directory to scan; default {', '.join(DEFAULT_ROOTS)}")
    parser.add_argument("--since", type=parse_duration, help="only transcripts changed within this time, for example 7d")
    parser.add_argument("--top", type=int, default=15, help="rows per table")
    parser.add_argument("--json", action="store_true", help="print JSON")
    args = parser.parse_args(argv)

    paths = [os.path.expanduser(path) for path in args.transcript]
    if not paths:
        paths = find_transcripts(args.root or DEFAULT_ROOTS, args.since)
    calls = []
    sessions = []
    for path in paths:
        session, items, first, last = read_transcript(path)
        if items:
            sessions.append(session)
            calls.extend(items)
    report = analyse(calls)
    report["transcripts"] = len(sessions)
    if args.json:
        json.dump(report, sys.stdout, indent=2)
        print()
    else:
        print_report(report, sessions, args.top)


if __name__ == "__main__":
    main()
