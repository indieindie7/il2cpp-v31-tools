"""Slim reading copies of Ghidra C dumps; every kept line is "N: text", N = line in the REAL dump.
usage: slim.py <dump dir|file.c>... [--out DIR] [--profile default|il2cpp] [--drop REGEX]...
Default profile drops only blank lines, lone braces and local declarations. --profile il2cpp adds the
IL2CPP boilerplate (class-init checks, null-check gotos); add your build's init stub calls with
--drop '^s*FUN_<addr>('. Cite the real dump with these numbers."""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402

TYPES = (r"(?:unsigned\s+)?(?:undefined\d?|longlong|ulonglong|int|uint|long|ulong|float|float10|double|char|uchar|"
         r"bool|byte|short|ushort|code|void|[A-Za-z_]\w*_t|[A-Z]\w+)")
BASE = [
    re.compile(r"^\s*$"),
    re.compile(r"^\s*[{}]\s*$"),
    re.compile(rf"^\s*{TYPES}\s*\**\s*\w+(\s*\[\w+\])?;\s*$"),
]
IL2CPP = [
    re.compile(r"^\s*if \(\*\(int \*\)\(_?DAT_[0-9a-f]+ \+ 0xe4\) == 0\) \{"),
    re.compile(r"^\s*if \(\w+ == 0\) goto (code_r0x|LAB_)[0-9a-f]+;"),
    re.compile(r"^\s*if \(DAT_[0-9a-f]+ == '\\0'\) \{"),
    re.compile(r"^\s*DAT_[0-9a-f]+ = '\\x01';"),
]
HDR_KEEP = re.compile(r"^// ==== ")


def patterns(profile, extra):
    pats = list(BASE)
    if profile == "il2cpp":
        pats += IL2CPP
    return pats + [re.compile(x) for x in extra]


def keep(line, pats):
    return bool(HDR_KEEP.match(line)) or not any(p.match(line) for p in pats)


def slim_file(src, dst, pats):
    lines = G.read_lines(src)
    out = [f"{n}: {t.rstrip()}" for n, t in enumerate(lines, 1) if keep(t, pats)]
    dst.write_text("\n".join(out) + "\n", encoding="utf-8")
    return len(lines), len(out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("dumps", nargs="+")
    ap.add_argument("--out", default="slim_out")
    ap.add_argument("--profile", choices=("default", "il2cpp"), default="default")
    ap.add_argument("--drop", action="append", default=[])
    a = ap.parse_args(argv)
    pats, out = patterns(a.profile, a.drop), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tot_a = tot_b = 0
    for f in G.collect(a.dumps):
        x, y = slim_file(f, out / f.name, pats)
        tot_a, tot_b = tot_a + x, tot_b + y
        print(f"{f.name} {x} -> {y} ({100 * y // max(x, 1)}%)")
    print(f"TOTAL {tot_a} -> {tot_b} lines, written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
