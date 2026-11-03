"""Shared helpers for the add-on's test-suite.

Import this first in every test module:

    from testlib import ADDON, BIN_DIR, run_cli, wait_for

Importing it puts the tests dir on sys.path, so sibling helpers import under
`python3 -m unittest discover -s tests` (run from `claudecode/`, as `make test` does).
Nothing here touches the network, Home Assistant or real tokens: a test that needs a
server starts one on 127.0.0.1 itself.
"""
import subprocess
import sys
import time
from pathlib import Path

# ---- source-tree constants ----------------------------------------------------------------
REPO = Path(__file__).resolve().parents[2]
ADDON = REPO / "claudecode"
BIN_DIR = ADDON / "rootfs/usr/local/bin"
TESTS_DIR = Path(__file__).resolve().parent

if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

SUPERVISOR_TOKEN = "test-supervisor-token"   # what tests hand to code that talks to the Supervisor


def run_cli(argv, env, timeout=60, cwd=None, input=None):
    """Run a command (list; Paths allowed) and return (returncode, stdout, stderr) as text.
    stdin is /dev/null unless `input` is given."""
    argv = [str(a) for a in argv]
    kw = {"stdin": subprocess.DEVNULL} if input is None else {"input": input}
    cp = subprocess.run(argv, env=env, cwd=str(cwd) if cwd else None, capture_output=True,
                        text=True, timeout=timeout, **kw)
    return cp.returncode, cp.stdout, cp.stderr


def wait_for(predicate, timeout=10, interval=0.05) -> bool:
    """Poll `predicate()` until it is truthy or `timeout` seconds pass."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return bool(predicate())
