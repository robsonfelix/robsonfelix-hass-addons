"""stdin-runner.sh: headless runs from `hassio.addon_stdin`, driven through a pipe.

A fake `claude` on PATH records its arguments and behaves per the prompt text; a local
HTTP server stands in for the Supervisor and records the events the runner fires. The
STDIN_RUNNER_* overrides point the runner's paths at a scratch directory.
"""
import json
import os
import shutil
import signal
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from testlib import ADDON, SUPERVISOR_TOKEN as TOKEN, wait_for

RUNNER = ADDON / "stdin-runner.sh"   # the Dockerfile copies it to /usr/local/bin

FAKE_CLAUDE = """#!/bin/bash
# Records its argv, then acts on the prompt text (the argument after -p).
printf '%s\\n' "$(printf '%q ' "$@")" >> "$FAKE_CLAUDE_ARGS"
prompt=""
while [ $# -gt 0 ]; do [ "$1" = "-p" ] && prompt="$2"; shift; done
case "$prompt" in
  *SLEEP*) sleep 60 ;;
  *FAIL*)  echo "boom" >&2; exit 3 ;;
  *)       echo "hello from fake claude" ;;
esac
"""


class Events:
    """Records every POST the runner makes to the fake Supervisor."""

    def __init__(self):
        self.items = []
        outer = self

        class H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                outer.items.append({"path": self.path, "auth": self.headers.get("Authorization"),
                                    "json": json.loads(body or b"{}")})
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"{}")

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()

    def of(self, name):
        return [e["json"] for e in self.items if e["path"] == f"/core/api/events/{name}"]

    def wait(self, name, n=1, timeout=15):
        if not wait_for(lambda: len(self.of(name)) >= n, timeout):
            raise AssertionError(f"event {name} (x{n}) not seen within {timeout}s; got {self.items}")
        return self.of(name)


class TestStdinRunner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="stdin-runner-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.events = Events()
        self.addCleanup(self.events.close)
        fakebin = os.path.join(self.tmp, "bin")
        os.mkdir(fakebin)
        with open(os.path.join(fakebin, "claude"), "w", encoding="utf-8") as f:
            f.write(FAKE_CLAUDE)
        os.chmod(os.path.join(fakebin, "claude"), 0o755)
        self.args_log = os.path.join(self.tmp, "claude-args")
        self.log_dir = os.path.join(self.tmp, "task-logs")
        self.run_dir = os.path.join(self.tmp, "run")
        self.options = os.path.join(self.tmp, "options.json")
        self.write_options({"default_task_model": "sonnet", "default_task_allowed_tools": ["mcp__homeassistant__*"],
                            "task_max_runtime_minutes": 1})
        self.env = dict(os.environ)
        self.env.update({
            "PATH": fakebin + os.pathsep + os.environ.get("PATH", ""),
            "SUPERVISOR_TOKEN": TOKEN,
            "FAKE_CLAUDE_ARGS": self.args_log,
            "STDIN_RUNNER_OPTIONS": self.options,
            "STDIN_RUNNER_LOG_DIR": self.log_dir,
            "STDIN_RUNNER_RUN_DIR": self.run_dir,
            "STDIN_RUNNER_SUPERVISOR_URL": self.events.url,
        })
        self.proc = None

    def write_options(self, opts):
        with open(self.options, "w", encoding="utf-8") as f:
            json.dump(opts, f)

    def start(self):
        # Through bash: the Dockerfile sets the exec bit at build time, git does not keep it.
        self.proc = subprocess.Popen(["bash", str(RUNNER)], env=self.env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True, start_new_session=True)
        self.addCleanup(self.stop)
        self.events.wait("claudecode_runner_ready")
        return self.proc

    def stop(self):
        if self.proc is None:
            return
        # The runner and its watcher subshell share the session start() gave them; a run's
        # `claude` sits in its own setsid group, named by the pgid file. That file outlives
        # the run, so only use it while a run is still active (started but not finished).
        if self.proc.poll() is None:
            os.killpg(self.proc.pid, signal.SIGKILL)
        if len(self.of_started()) > len(self.events.of("claudecode_run_finished")):
            try:
                with open(os.path.join(self.run_dir, "pgid"), encoding="utf-8") as f:
                    os.killpg(int(f.read().strip()), signal.SIGKILL)   # a fake claude left sleeping
            except (OSError, ValueError):
                pass
        self.proc.wait(timeout=10)
        for pipe in (self.proc.stdin, self.proc.stdout):
            if pipe and not pipe.closed:
                pipe.close()
        self.proc = None

    def of_started(self):
        return self.events.of("claudecode_run_started")

    def send(self, obj):
        line = obj if isinstance(obj, str) else json.dumps(obj)
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()

    def claude_calls(self):
        try:
            with open(self.args_log, encoding="utf-8") as f:
                return f.read().splitlines()
        except FileNotFoundError:
            return []

    # ---- tests ------------------------------------------------------------------------------

    def test_ready_event_carries_the_default_model_and_the_token(self):
        self.start()
        ready = self.events.items[0]
        self.assertEqual(ready["path"], "/core/api/events/claudecode_runner_ready")
        self.assertEqual(ready["auth"], f"Bearer {TOKEN}")
        self.assertEqual(ready["json"], {"model": "sonnet"})

    def test_task_runs_claude_with_defaults_and_reports_both_events(self):
        self.start()
        self.send({"prompt": "say hi", "run_id": "t1"})
        started = self.events.wait("claudecode_run_started")
        self.assertEqual(started[0]["run_id"], "t1")
        self.assertTrue(started[0]["log_path"].startswith(self.log_dir + "/t1-"))
        fin = self.events.wait("claudecode_run_finished")[0]
        self.assertEqual((fin["run_id"], fin["success"], fin["exit_code"], fin["aborted"]), ("t1", True, 0, False))
        self.assertIn("hello from fake claude", fin["output_tail"])
        self.assertIn("duration_seconds", fin)
        with open(fin["log_path"], encoding="utf-8") as f:
            self.assertIn("hello from fake claude", f.read())
        self.assertEqual(self.claude_calls(),
                         [r"-p say\ hi --model sonnet --allowedTools mcp__homeassistant__\* "])

    def test_task_fields_override_the_option_defaults(self):
        self.start()
        self.send({"prompt": "x", "model": "opus", "allowed_tools": ["Bash", "Read"]})
        self.events.wait("claudecode_run_finished")
        self.assertEqual(self.claude_calls(),
                         ["-p x --model opus --allowedTools Bash --allowedTools Read "])

    def test_prompt_file(self):
        path = os.path.join(self.tmp, "task.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write("from a file")
        self.start()
        self.send({"prompt_file": path, "run_id": "pf"})
        fin = self.events.wait("claudecode_run_finished")[0]
        self.assertTrue(fin["success"])
        self.assertIn(r"-p from\ a\ file", self.claude_calls()[0])

    def test_missing_prompt_is_reported_not_run(self):
        self.start()
        self.send({"run_id": "np"})
        fin = self.events.wait("claudecode_run_finished")[0]
        self.assertEqual(fin, {"run_id": "np", "success": False, "error": "no prompt provided"})
        self.assertEqual(self.claude_calls(), [])
        self.assertEqual(self.events.of("claudecode_run_started"), [])

    def test_failing_claude_reports_exit_code_and_stderr_tail(self):
        self.start()
        self.send({"prompt": "please FAIL", "run_id": "f"})
        fin = self.events.wait("claudecode_run_finished")[0]
        self.assertEqual((fin["success"], fin["exit_code"]), (False, 3))
        self.assertIn("boom", fin["output_tail"])

    def test_second_task_while_busy_is_rejected_and_abort_kills_the_run(self):
        self.start()
        self.send({"prompt": "SLEEP", "run_id": "long"})
        self.events.wait("claudecode_run_started")
        self.send({"prompt": "x", "run_id": "second"})
        rej = self.events.wait("claudecode_run_rejected")[0]
        self.assertEqual(rej, {"run_id": "second", "reason": "another run is active"})
        self.assertEqual(self.events.of("claudecode_run_finished"), [])
        self.send({"abort": True})
        fin = self.events.wait("claudecode_run_finished", timeout=30)[0]
        self.assertEqual((fin["run_id"], fin["success"], fin["aborted"]), ("long", False, True))
        self.assertEqual(len(self.claude_calls()), 1)   # "second" never ran

    def test_non_json_line_is_ignored_and_the_runner_carries_on(self):
        self.start()
        self.send("this is not json")
        self.send({"prompt": "after", "run_id": "ok"})
        fin = self.events.wait("claudecode_run_finished")[0]
        self.assertEqual(fin["run_id"], "ok")

    def test_abort_with_nothing_running_is_harmless(self):
        self.start()
        self.send({"abort": True})
        self.send({"prompt": "x", "run_id": "later"})
        self.assertEqual(self.events.wait("claudecode_run_finished")[0]["run_id"], "later")

    def test_runner_exits_when_stdin_closes(self):
        self.start()
        self.proc.stdin.close()
        self.assertEqual(self.proc.wait(timeout=15), 0)
        out = self.proc.stdout.read()
        self.assertIn("stdin closed", out)
        self.assertIn("task runner ready", out)


if __name__ == "__main__":
    unittest.main()
