"""Make Ghidra name list (ghidra/names.txt) and dump lists from tables/methods.tsv."""
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ("Assembly-CSharp.dll", "Assembly-CSharp-firstpass.dll")
SHARED_MAX = 3


def clean(s):
    return re.sub(r"[^A-Za-z0-9_]", "_", s.replace("/", "_"))


def load_rows():
    with open(ROOT / "tables" / "methods.tsv", encoding="utf-8") as f:
        f.readline()
        return [l.rstrip("\n").split("\t") for l in f]


def name_rows(rows):
    """Return list of (va, name, class, method, token) for unique-address methods."""
    use = Counter(r[7] for r in rows if r[7])
    dup = Counter((r[0], r[2], r[3]) for r in rows)
    out = []
    for r in rows:
        if not r[7] or use[r[7]] > SHARED_MAX:
            continue
        nm = clean(r[2]) + "__" + clean(r[3])
        if dup[(r[0], r[2], r[3])] > 1:
            nm += "_" + r[4][-4:]
        out.append((r[7], nm, r[2], r[3], r[0]))
    return out


def main():
    allimg = "all" in sys.argv[1:]
    rows = [r for r in load_rows() if allimg or r[0] in IMAGES]
    named = name_rows(rows)
    with open(ROOT / "ghidra" / "names.txt", "w", encoding="utf-8") as f:
        for va, nm, *_ in named:
            f.write(f"{va} {nm}\n")
    print("names written", len(named), "of", len(rows))


if __name__ == "__main__":
    main()
