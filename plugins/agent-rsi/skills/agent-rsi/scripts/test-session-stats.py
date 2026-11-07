#!/usr/bin/env python3
"""Tests for session-stats.py. Run: python3 -I test-session-stats.py"""
import importlib.util
import json
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("session_stats", os.path.join(HERE, "session-stats.py"))
stats = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stats)


def claude_use(stamp, message_id, tool_id, command, background=False):
    return {"timestamp": stamp, "message": {"id": message_id, "content": [
        {"type": "tool_use", "id": tool_id, "name": "Bash", "input": {"command": command, "run_in_background": background}},
    ]}}


def claude_result(stamp, tool_id, output, is_error=False):
    return {"timestamp": stamp, "message": {"content": [
        {"type": "tool_result", "tool_use_id": tool_id, "content": output, "is_error": is_error},
    ]}}


class CommandFamilyTest(unittest.TestCase):
    cases = {
        "git status --short": "git status",
        "cd /w; export A=1; git diff --quiet -- f; pnpm -F @a/b exec vitest run x": "pnpm exec vitest",
        'R="timeout 900 tool -n ns"; $R worktree add -r r --name n': "tool worktree add",
        "timeout 400 tool -n ns workspace create name --size 1": "tool workspace create",
        "tool -n ns exec --cwd /w my-workspace -- sh -c x": "tool exec",
        "python3 - <<'EOF'\nimport json\nconst x = 1\nEOF\nnpx vitest": "npx vitest",
        "python3 -I - <<'EOF'\nimport json\nEOF": "python3 inline",
        'base=$(git merge-base origin/main HEAD); TURBO_SCM_BASE="$base" pnpm exec turbo run test': "pnpm exec turbo",
        "for i in $(seq 1 5); do gh pr checks 1 --repo a/b; sleep 5; done": "gh pr checks",
        "until tool -n x inspect p | grep -q Ok; do sleep 15; done": "tool inspect",
        "cd a && . ./env.sh && npx -y pnpm@1 verify": "npx",
        "echo hi": "echo",
        "kubectl -n a get pods": "kubectl get",
        "cmd_a >/dev/null 2>&1 || (do_b > /dev/null)": "cmd_a",
        'python3 -c "import json\nprint(1)"': "python3 inline",
        "while true; do for id in 1 2; do gh run view $id; done; done": "gh run view",
    }

    def test_families(self):
        for command, family in self.cases.items():
            with self.subTest(command=command):
                self.assertEqual(stats.command_family("Bash", command), family)


class TranscriptTest(unittest.TestCase):
    def write(self, entries):
        handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        for entry in entries:
            handle.write(json.dumps(entry) + "\n")
        handle.write("not json\n")
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def test_claude_pairs_batches_background_and_errors(self):
        path = self.write([
            claude_use("2026-01-01T00:00:00Z", "m1", "t1", "git status"),
            claude_result("2026-01-01T00:00:12Z", "t1", "ok"),
            # Two calls in one message are a parallel batch.
            claude_use("2026-01-01T00:01:00Z", "m2", "t2", "sed -n 1p f"),
            claude_use("2026-01-01T00:01:00Z", "m2", "t3", "pnpm test"),
            claude_result("2026-01-01T00:11:00Z", "t2", "x"),
            claude_result("2026-01-01T00:11:00Z", "t3", "Exit code 1"),
            claude_use("2026-01-01T00:12:00Z", "m3", "t4", "pnpm dev", background=True),
            claude_result("2026-01-01T00:12:01Z", "t4", "Command running in background with ID: b1"),
            claude_use("2026-01-01T00:13:00Z", "m4", "t5", "rm -rf /"),
            claude_result("2026-01-01T00:13:30Z", "t5", "The user doesn't want to proceed with this tool use.", is_error=True),
        ])
        _, calls, _, _ = stats.read_transcript(path)
        by_command = {call.command: call for call in calls}
        self.assertEqual(len(calls), 5)
        self.assertEqual(by_command["git status"].seconds, 12)
        self.assertEqual(by_command["pnpm test"].batch, 2)
        self.assertTrue(by_command["pnpm test"].error)
        self.assertTrue(by_command["pnpm dev"].background)
        self.assertTrue(by_command["rm -rf /"].denied)

        report = stats.analyse(calls)
        self.assertEqual(report["batched_calls"], 2)
        self.assertEqual(report["background_calls"], 1)
        # The batch counts once in the total, and neither batched call gets its time.
        self.assertEqual(report["tool_seconds"], 12 + 600 + 30)
        families = {row["family"]: row for row in report["families"]}
        self.assertEqual(families["pnpm test"]["seconds"], 0)
        self.assertTrue(any("parallel batches" in finding for finding in report["findings"]))
        self.assertTrue(any("denied" in finding for finding in report["findings"]))

    def test_codex_calls(self):
        path = self.write([
            {"timestamp": "2026-01-01T00:00:00Z", "type": "response_item", "payload": {
                "type": "custom_tool_call", "call_id": "c1", "name": "exec",
                "input": 'text(await tools.exec_command({cmd:"pnpm -F a typecheck", yield_time_ms:1000}))'}},
            {"timestamp": "2026-01-01T00:00:40Z", "type": "response_item", "payload": {
                "type": "custom_tool_call_output", "call_id": "c1", "output": [{"type": "input_text", "text": "Process exited with code 2"}]}},
            {"timestamp": "2026-01-01T00:01:00Z", "type": "response_item", "payload": {
                "type": "function_call", "call_id": "c2", "name": "shell", "arguments": json.dumps({"command": ["git", "fetch"]})}},
            {"timestamp": "2026-01-01T00:01:05Z", "type": "response_item", "payload": {
                "type": "function_call_output", "call_id": "c2", "output": "done"}},
        ])
        _, calls, _, _ = stats.read_transcript(path)
        self.assertEqual([call.family for call in calls], ["pnpm typecheck", "git fetch"])
        self.assertEqual([call.seconds for call in calls], [40, 5])
        self.assertTrue(calls[0].error)

    def test_fixed_cost_and_polling_findings(self):
        entries = []
        for index in range(30):
            minute = f"2026-01-01T00:{index:02d}"
            entries.append(claude_use(f"{minute}:00Z", f"m{index}", f"t{index}", f"tool -n ns exec ws -- echo {index}"))
            entries.append(claude_result(f"{minute}:11Z", f"t{index}", "hi"))
        entries.append(claude_use("2026-01-01T01:00:00Z", "p", "tp", "until tool inspect x | grep -q Done; do sleep 15; done"))
        entries.append(claude_result("2026-01-01T01:06:00Z", "tp", ""))
        _, calls, _, _ = stats.read_transcript(self.write(entries))
        findings = stats.analyse(calls)["findings"]
        self.assertTrue(any("`tool exec` ran 30 times and three quarters took 11.0s" in finding for finding in findings), findings)
        self.assertTrue(any("polling loops" in finding for finding in findings), findings)

    def test_redact(self):
        text = stats.redact("ssh user@example.com https://k8s.example.com:6443/x 192.0.2.7 /home/example/x")
        self.assertNotIn("example.com:6443", text)
        self.assertNotIn("user@example.com", text)
        self.assertNotIn("192.0.2.7", text)
        self.assertIn("/home/user/x", text)


if __name__ == "__main__":
    unittest.main()
