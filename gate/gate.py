"""Read-loop gate for any Ghidra C dump: every non-trivial function needs a note cite inside its body.
usage: gate.py <tag> --dumps <dir|file.c>... --notes <file|dir>... [--min-lines 12] [--trivial-name RE]
                    [--profile default|il2cpp] [File.c[:A-B] ...]
Cite = File.c:A-B (also File.c:N, lists 'File.c:1-5, 9', and bare '(7-9)' after a named file).
Strict rule: a function is READ only if one cite lies wholly inside that function (header line to its
last line) and contains at least one non-blank line AFTER the '// ==== name' header. A cite that
crosses a function boundary, touches only a header/blank lines, lies outside every function or names
an unknown file covers nothing and is listed as BADCITE (warning). Exit 1 while UNREAD n > 0."""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402

IL2CPP_TRIVIAL = r"^(\.?c?ctor|_c?ctor|(De)?[Ss]erialize(All)?)$"


def trivial(name, size, args):
    if size < args.min_lines:
        return True
    if args.profile == "il2cpp":
        base = name.split("__", 1)[-1]
        if re.search(IL2CPP_TRIVIAL, base) or (base.startswith(("get_", "set_")) and size < 20):
            return True
    return bool(args.trivial_name and re.search(args.trivial_name, name))


def classify(d, a, b, after_header=False):
    """-> (state, function index or None) for a cite [a, b] in dump d."""
    if a > b:
        return "reversed", None
    i = d.locate(a)
    if i < 0:
        return "outside", None
    name, start, end = d.funcs[i]
    if b > end:
        return ("span" if b <= len(d.lines) else "outside"), i
    if after_header and a <= start:
        return "header-start", i
    if d.nb(max(a, start + 1), b) == 0:
        return "header-only", i
    return "ok", i


def deep_enough(d, key, hit, bucket):
    """a long function needs cites in at least half of its <bucket>-line slices (0 = rule off)"""
    start, end = d.funcs[key[1]][1:]
    return not bucket or 2 * len(hit) >= (end - start) // bucket + 1


def apply_cites(dumps, cites, after_header=False, bucket=0):
    """-> (set of (dump name, func index) read, list of bad-cite messages)"""
    by_name, hits, bad = {}, {}, []
    for d in dumps:
        by_name.setdefault(d.name.lower(), []).append(d)
    for fname, a, b, ln in cites:
        targets = by_name.get(fname.lower())
        if not targets:
            bad.append(f"{ln} {fname}:{a}-{b} unknown file")
            continue
        for d in targets:
            state, i = classify(d, a, b, after_header)
            if state == "ok":
                lo = d.funcs[i][1]
                span = range((a - lo) // bucket, (b - lo) // bucket + 1) if bucket else (0,)
                hits.setdefault((d.name, i), (d, set()))[1].update(span)
            else:
                bad.append(f"{ln} {fname}:{a}-{b} {state}")
    read = {k for k, (d, hit) in hits.items() if deep_enough(d, k, hit, bucket)}
    return read, bad


def parse_filter(tokens):
    flt = {}
    for t in tokens:
        name, _, rng = t.partition(":")
        lo, hi = (int(x) for x in rng.split("-")) if rng else (0, 10 ** 9)
        flt.setdefault(name.lower(), []).append((lo, hi))
    return flt


def in_filter(flt, dname, start):
    if not flt:
        return True
    return any(lo <= start <= hi for lo, hi in flt.get(dname.lower(), []))


def unread(dumps, read, flt, args):
    out = []
    for d in dumps:
        for i, (name, start, end) in enumerate(d.funcs):
            size = end - start + 1
            if (d.name, i) in read or trivial(name, size, args):
                continue
            if in_filter(flt, d.name, start):
                out.append((d.name, start, size, name))
    return out


def split_filters(args):
    """argparse nargs='+' swallows trailing 'File.c:A-B' filters; move non-paths back out."""
    flt = list(args.filters)
    for attr in ("dumps", "notes"):
        keep = []
        for v in getattr(args, attr):
            (flt if G.FILTER.match(v) and not Path(v).exists() else keep).append(v)
        setattr(args, attr, keep)
    return flt


def all_cites(paths):
    """Cites of every notes file; each carries 'notesfile:line' as its location."""
    out = []
    for f in G.collect(paths, "*.md"):
        text = f.read_text(encoding="utf-8", errors="replace")
        out += G.parse_cites(text, f.name)
    return out


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("tag")
    ap.add_argument("filters", nargs="*")
    ap.add_argument("--dumps", nargs="+", required=True)
    ap.add_argument("--notes", nargs="+", required=True)
    ap.add_argument("--min-lines", type=int, default=12)
    ap.add_argument("--trivial-name", default="")
    ap.add_argument("--profile", choices=("default", "il2cpp"), default="default")
    ap.add_argument("--quiet-bad", action="store_true")
    ap.add_argument("--after-header", action="store_true", help="a cite must START below the header line")
    ap.add_argument("--bucket", type=int, default=200, help="depth rule: cites must touch half of a function's N-line slices (0 = off)")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    flt = parse_filter(split_filters(args))
    dumps = [G.Dump(p) for p in G.collect(args.dumps)]
    if not any(d.funcs for d in dumps):
        print("NO FUNCTIONS parsed from --dumps (wrong path, or a slim copy?): gate cannot pass")
        return 2
    read, bad = apply_cites(dumps, all_cites(args.notes), args.after_header, args.bucket)
    left = unread(dumps, read, flt, args)
    for f, start, size, name in left:
        print(f"{f}:{start}\t{size} lines\t{name}")
    if not args.quiet_bad:
        for b in bad:
            print("BADCITE " + b)
    print(f"[{args.tag}] functions {sum(len(d.funcs) for d in dumps)}, read {len(read)}, BADCITE {len(bad)}")
    print("UNREAD", len(left))
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main())
