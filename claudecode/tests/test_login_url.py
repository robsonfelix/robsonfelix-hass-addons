"""claude-login-url: pulls the OAuth URL out of the `claude` tmux session into a file.

Runs a real tmux on a private socket (TMUX_TMPDIR), so nothing here touches a user's
tmux server. The window is 60 columns wide, so the URL soft-wraps over several rows and
the test proves `capture-pane -J` rejoins it.
"""
import os
import shlex
import shutil
import subprocess
import tempfile
import unittest

from testlib import BIN_DIR, run_cli, wait_for

SCRIPT = BIN_DIR / "claude-login-url"
URL = "https://claude.ai/oauth/authorize?code=true&client_id=" + "9d1c250a-e61b-44d9-88ed-5944d1962f5e" * 3 + "&state=xyz"
OLDER = "https://claude.ai/oauth/authorize?code=true&state=older"
BANNER = "Browser didn't open? Use the url below to sign in:"


@unittest.skipUnless(shutil.which("tmux"), "tmux not installed")
class TestClaudeLoginUrl(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="login-url-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.env = {k: v for k, v in os.environ.items() if k != "TMUX"}
        self.env["TMUX_TMPDIR"] = self.tmp          # private tmux server
        self.out = os.path.join(self.tmp, "url.txt")
        self.addCleanup(lambda: subprocess.run(["tmux", "kill-server"], env=self.env, capture_output=True, check=False))

    def tmux(self, *args):
        return subprocess.run(["tmux", *args], env=self.env, capture_output=True, text=True, check=False)

    def start_session(self, *lines):
        """A `claude` session whose first window prints `lines` and then idles."""
        cmd = "printf '%s\\n' " + " ".join(shlex.quote(l) for l in lines) + "; sleep 120"
        r = self.tmux("new-session", "-d", "-s", "claude", "-x", "60", "-y", "12", cmd)
        self.assertEqual(r.returncode, 0, r.stderr)
        last = lines[-1][-20:] if lines else ""
        self.assertTrue(wait_for(lambda: last in self.tmux("capture-pane", "-p", "-J", "-t", "claude").stdout),
                        "pane never showed the text")

    def run_script(self):
        # Through bash: the Dockerfile sets the exec bit at build time, git does not keep it.
        rc, out, err = run_cli(["bash", SCRIPT, self.out], self.env, timeout=30)
        return subprocess.CompletedProcess([str(SCRIPT), self.out], rc, out, err)

    def test_wrapped_url_is_rejoined_and_saved_with_mode_600(self):
        self.start_session(BANNER, URL)
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(self.out, encoding="utf-8") as f:
            self.assertEqual(f.read(), URL + "\n")
        self.assertEqual(os.stat(self.out).st_mode & 0o777, 0o600)
        self.assertIn(self.out, r.stdout)

    def test_newest_url_wins(self):
        self.start_session(OLDER, "...", URL)
        self.assertEqual(self.run_script().returncode, 0)
        with open(self.out, encoding="utf-8") as f:
            self.assertEqual(f.read().strip(), URL)

    def test_no_session(self):
        r = self.run_script()
        self.assertEqual(r.returncode, 1)
        self.assertIn("No tmux session named 'claude'", r.stderr)
        self.assertFalse(os.path.exists(self.out))

    def test_no_url_in_session(self):
        self.start_session("Welcome to Claude Code", "https://example.com/not-a-login")
        r = self.run_script()
        self.assertEqual(r.returncode, 1)
        self.assertIn("No login URL found", r.stderr)
        self.assertFalse(os.path.exists(self.out))


if __name__ == "__main__":
    unittest.main()
