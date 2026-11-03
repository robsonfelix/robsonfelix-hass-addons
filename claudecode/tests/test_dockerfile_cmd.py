"""The Dockerfile's CMD starts the add-on: make sure what it names parses.

Two shapes are accepted. `CMD ["/path/to/script"]` must name a script in rootfs/ that
`bash -n` accepts. `CMD ["/bin/bash", "-c", "<script>"]` is a bash script inside a JSON
string: Docker joins the continuation lines (a trailing backslash) before reading the
JSON array, so rebuild it the same way and parse the string with `bash -n -c`.
"""
import json
import re
import subprocess
import unittest

from testlib import ADDON

DOCKERFILE = ADDON / "Dockerfile"
ROOTFS = ADDON / "rootfs"


def instruction(name):
    """The joined text of the last `name` instruction (the one Docker honours), continuation
    lines folded and comment lines inside a continued instruction skipped, like Docker does."""
    found = []
    out = []
    for line in DOCKERFILE.read_text(encoding="utf-8").splitlines():
        if out and line.lstrip().startswith("#"):
            continue
        if out or re.match(name + r"[ \t]", line, re.IGNORECASE):
            if line.rstrip().endswith("\\"):
                out.append(line.rstrip()[:-1])
            else:
                out.append(line)
                found.append("".join(out)[len(name):].strip())
                out = []
    if not found:
        raise AssertionError(f"no {name} instruction in {DOCKERFILE}")
    return found[-1]


class TestDockerfileCmd(unittest.TestCase):
    def setUp(self):
        self.cmd = json.loads(instruction("CMD"))
        self.assertIsInstance(self.cmd, list, "CMD must use the JSON array form")

    def test_cmd_parses(self):
        if self.cmd[:2] == ["/bin/bash", "-c"]:
            self.assertEqual(len(self.cmd), 3, "CMD should be exactly /bin/bash -c <script>")
            r = subprocess.run(["bash", "-n", "-c", self.cmd[2]], capture_output=True, text=True, check=False)
            self.assertEqual(r.returncode, 0, r.stderr)
            # The last command must replace the shell, or ttyd runs as a child
            # that never gets the container's signals.
            self.assertIn("exec ttyd", self.cmd[2])
        else:
            script = ROOTFS / self.cmd[0].lstrip("/")
            self.assertTrue(script.is_file(), f"{self.cmd[0]} is not shipped in rootfs/")
            r = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True, check=False)
            self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
