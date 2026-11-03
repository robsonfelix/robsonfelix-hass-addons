"""ha-ws against a fake Home Assistant WebSocket server: the greeting that shares a read with
the HTTP 101, stop-on-failure vs --keep-going, non-result replies, timeouts and one-line errors."""
import json
import os
import socket
import subprocess
import sys
import threading
import time
import unittest

from testlib import BIN_DIR

HA_WS = BIN_DIR / "ha-ws"


def frame(obj):
    p = json.dumps(obj).encode()
    n = len(p)
    return bytes([0x81]) + (bytes([n]) if n < 126 else bytes([126]) + n.to_bytes(2, "big")) + p


def read_exact(c, n):
    d = b""
    while len(d) < n:
        chunk = c.recv(n - len(d))
        if not chunk:
            raise ConnectionError
        d += chunk
    return d


def read_msg(c):
    h = read_exact(c, 2)
    n = h[1] & 0x7F
    if n == 126:
        n = int.from_bytes(read_exact(c, 2), "big")
    mask = read_exact(c, 4)
    return json.loads(bytes(b ^ mask[i % 4] for i, b in enumerate(read_exact(c, n))))


class TestHaWs(unittest.TestCase):
    def setUp(self):
        self.srv = socket.socket()
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen(1)
        self.addCleanup(self.srv.close)
        self.seen = []
        threading.Thread(target=self.serve, daemon=True).start()

    def serve(self):
        try:
            c, _ = self.srv.accept()
            self.addCleanup(c.close)
            d = b""
            while b"\r\n\r\n" not in d:
                d += c.recv(4096)
            # One write on purpose: 101 + auth_required arrive in the same read.
            c.sendall(b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n"
                      b"Connection: Upgrade\r\n\r\n" + frame({"type": "auth_required"}))
            read_msg(c)
            c.sendall(frame({"type": "auth_ok"}))
            while True:
                m = read_msg(c)
                self.seen.append(m["type"])
                if m["type"] == "ping":
                    c.sendall(frame({"id": m["id"], "type": "pong"}))
                elif m["type"] == "slow":
                    time.sleep(5)
                elif m["type"] == "never":      # no reply, but heartbeat pings and events keep coming
                    for _ in range(40):
                        c.sendall(bytes([0x89, 0]) + frame({"id": 99, "type": "event"}))
                        time.sleep(0.2)
                else:
                    c.sendall(frame({"id": m["id"], "type": "result", "success": m["type"] != "bad"}))
        except (OSError, ConnectionError):
            pass

    def run_ws(self, *args, token="x"):
        src = HA_WS.read_text().replace('HOST = "supervisor"', 'HOST = "127.0.0.1"') \
                               .replace("PORT = 80", f"PORT = {self.srv.getsockname()[1]}")
        env = dict(os.environ, SUPERVISOR_TOKEN=token)
        return subprocess.run([sys.executable, "-c", src, *args], capture_output=True, text=True,
                              env=env, timeout=60)

    def test_greeting_coalesced_with_handshake(self):
        r = self.run_ws('{"type": "get_config"}')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), {"id": 1, "type": "result", "success": True})

    def test_non_result_reply_is_printed(self):
        r = self.run_ws('{"type": "ping"}')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["type"], "pong")

    def test_stops_at_first_failure(self):
        r = self.run_ws('[{"type": "a"}, {"type": "bad"}, {"type": "c"}]')
        self.assertEqual(r.returncode, 1)
        self.assertEqual(len(r.stdout.splitlines()), 2)
        self.assertIn("were not sent", r.stderr)
        self.assertEqual(self.seen, ["a", "bad"])

    def test_keep_going_runs_the_rest(self):
        r = self.run_ws("--keep-going", '[{"type": "a"}, {"type": "bad"}, {"type": "c"}]')
        self.assertEqual(r.returncode, 1)
        self.assertEqual(len(r.stdout.splitlines()), 3)

    def test_errors_are_one_line_exit_2(self):
        for args, text in ((("--timeout", "1", '{"type": "slow"}'), "no reply to command 1"),
                           (("{nope",), "not valid JSON"),
                           (("/nonexistent.json",), "cannot read"),
                           (('[{"no_type": 1}]',), "not an object with a \"type\""),
                           ((), "expected exactly one argument")):
            r = self.run_ws(*args)
            self.assertEqual(r.returncode, 2, args)
            self.assertIn(text, r.stderr)
            self.assertNotIn("Traceback", r.stderr)
            self.assertEqual(len(r.stderr.strip().splitlines()), 1, r.stderr)

    def test_timeout_is_a_deadline_not_an_idle_timer(self):
        t = time.monotonic()
        r = self.run_ws("--timeout", "1", '{"type": "never"}')
        self.assertEqual(r.returncode, 2)
        self.assertIn("no reply to command 1 (never) within 1 s", r.stderr)
        self.assertLess(time.monotonic() - t, 5)

    def test_missing_token(self):
        r = self.run_ws('{"type": "a"}', token="")
        self.assertEqual(r.returncode, 2)
        self.assertIn("SUPERVISOR_TOKEN is not set", r.stderr)


if __name__ == "__main__":
    unittest.main()
