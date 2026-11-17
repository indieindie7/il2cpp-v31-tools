"""Split ghidra/dump_<group>.c into ghidra/dump_<group>/<Class>.c (one file per class).
usage: il2split.py <group>
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "ghidra"
HDR = re.compile(r"^// ==== (\S+?)__")


def split(text):
    parts = {}
    cur = None
    for line in text.splitlines(keepends=True):
        m = HDR.match(line)
        if m:
            cur = m.group(1)
        if cur:
            parts.setdefault(cur, []).append(line)
    return parts


def main():
    group = sys.argv[1]
    text = (ROOT / f"dump_{group}.c").read_text(encoding="utf-8", errors="replace")
    out = ROOT / f"dump_{group}"
    out.mkdir(exist_ok=True)
    parts = split(text)
    for cls, lines in parts.items():
        (out / f"{cls}.c").write_text("".join(lines), encoding="utf-8")
    top = sorted(((len(v), k) for k, v in parts.items()), reverse=True)[:5]
    print(group, len(parts), "files; largest", top)


if __name__ == "__main__":
    main()
