"""Every shell script the add-on ships parses (`bash -n`, or `sh -n` for a #!/bin/sh script).

Cheap, and it catches the class of error that only shows up as a container that
never gets to ttyd: an unbalanced quote or a stray `fi` in a script nobody ran since
the edit.
"""
import subprocess
import unittest

from testlib import ADDON

EXTRA = [ADDON / "rootfs/root/.bashrc"]   # no shebang, sourced by bash


def shebang(path):
    try:
        with path.open("rb") as f:
            return f.readline()
    except OSError:
        return b""


def shell_scripts():
    for p in sorted(ADDON.rglob("*")):
        if not p.is_file() or "tests" in p.parts:
            continue
        line = shebang(p)
        if line.startswith(b"#!") and (b"bash" in line or line.rstrip().endswith(b"/sh")):
            yield p, ("bash" if b"bash" in line else "sh")
    for p in EXTRA:
        yield p, "bash"


class TestShellSyntax(unittest.TestCase):
    def test_every_script_parses(self):
        scripts = list(shell_scripts())
        self.assertGreaterEqual(len(scripts), 4, [str(p) for p, _ in scripts])
        for path, shell in scripts:
            with self.subTest(script=str(path.relative_to(ADDON))):
                r = subprocess.run([shell, "-n", str(path)], capture_output=True, text=True, check=False)
                self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
