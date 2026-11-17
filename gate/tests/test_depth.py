"""Synthetic test of the gate (no game content): one 500-line function, depth rule + zero-function exit.
run: py -3 tests/test_depth.py"""
import subprocess
import sys
import tempfile
from pathlib import Path

GATE = Path(__file__).resolve().parent.parent / "gate.py"


def run(tmp, notes, *extra):
    (tmp / "n.md").write_text(notes, encoding="utf-8")
    cmd = [sys.executable, str(GATE), "t", "--dumps", str(tmp / "big.c"), "--notes", str(tmp / "n.md"), *extra]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout.strip().splitlines()[-1]


def main():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        body = "\n".join(f"  x = x + {i};" for i in range(497))
        (tmp / "big.c").write_text(f"// ==== big_func @ 0x1000\nvoid big_func(void)\n{body}\n", encoding="utf-8")
        cases = [("one cite", "big.c:5-10", (), (1, "UNREAD 1")),
                 ("bucket off", "big.c:5-10", ("--bucket", "0"), (0, "UNREAD 0")),
                 ("two slices", "big.c:5-10 and big.c:250-260", (), (0, "UNREAD 0")),
                 ("no notes", "nothing", (), (1, "UNREAD 1"))]
        bad = 0
        for name, notes, extra, want in cases:
            got = run(tmp, notes, *extra)
            print("ok  " if got == want else "FAIL", name, got)
            bad += got != want
        (tmp / "big.c").write_text("int x;\n", encoding="utf-8")
        code, _ = run(tmp, "big.c:1")
        print("ok  " if code == 2 else "FAIL", "zero functions -> exit", code)
        return 1 if bad or code != 2 else 0


if __name__ == "__main__":
    sys.exit(main())
