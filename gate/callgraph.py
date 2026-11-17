"""Caller/callee table from Ghidra C dump text, any naming style (FUN_xxx, hand names, Class__Method).
usage: callgraph.py callers|callees|table <NAME|ALL> --dumps <dir|file.c>... [--min-count 1]
Edges: function A mentions function B (defined in the dumps) as `B(`  -> call; as `PTR_B` -> ptr
(indirect call through a pointer table slot named after B); any other bare mention -> ref.
Only text is used: no indirect call is resolved beyond the PTR_ naming. `Class.Method` = `Class__Method`.
table prints: caller<TAB>callee<TAB>calls<TAB>ptr<TAB>ref."""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402

IDENT = re.compile(r"[A-Za-z_]\w*")


def edge_kind(tok, names, after):
    """-> (callee, kind) or None for one identifier token; `after` = text following it."""
    if tok in names:
        return tok, ("call" if after.lstrip().startswith("(") else "ref")
    if tok.startswith("PTR_") and tok[4:] in names:
        return tok[4:], "ptr"
    return None


def body_edges(text, names):
    cnt = Counter()
    for m in IDENT.finditer(text):
        hit = edge_kind(m.group(0), names, text[m.end():m.end() + 4])
        if hit:
            cnt[hit] += 1
    return cnt


COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)


def strip_comments(text):
    return COMMENT.sub(" ", text)


def drop_signature(lines, name):
    """Remove the function's own definition line so it does not count as a self-call."""
    pat = re.compile(rf"\b{re.escape(name)}\s*\(")
    seen = 0
    for i, t in enumerate(lines):
        if not t.strip():
            continue
        if pat.search(t) and not t.rstrip().endswith(";"):
            return lines[i + 1:]
        seen += 1
        if seen >= 3:
            break
    return lines


def build(dumps):
    """-> {(caller, callee): Counter(kind)} ; names may repeat across files (merged)."""
    funcs = [(d, f) for d in dumps for f in d.funcs]
    names = {f[0] for _, f in funcs}
    graph = {}
    for d, (name, start, end) in funcs:
        clean = strip_comments("\n".join(d.lines[start:end])).splitlines()
        text = "\n".join(drop_signature(clean, name))
        for (callee, kind), n in body_edges(text, names).items():
            graph.setdefault((name, callee), Counter())[kind] += n
    return graph


def norm(name):
    return name.replace(".", "__")


def wanted(mode, name, a, b):
    if name == "ALL":
        return True
    if mode == "callers":
        return b == name
    return a == name if mode == "callees" else name in (a, b)


def rows(graph, mode, name):
    name = norm(name)
    for (a, b), c in sorted(graph.items()):
        if wanted(mode, name, a, b):
            yield a, b, c


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("callers", "callees", "table"))
    ap.add_argument("name")
    ap.add_argument("--dumps", nargs="+", required=True)
    ap.add_argument("--min-count", type=int, default=1)
    a = ap.parse_args(argv)
    graph = build([G.Dump(p) for p in G.collect(a.dumps)])
    n = 0
    for caller, callee, c in rows(graph, a.mode, a.name):
        if sum(c.values()) < a.min_count:
            continue
        print(f"{caller}\t{callee}\t{c['call']}\t{c['ptr']}\t{c['ref']}")
        n += 1
    print(f"EDGES {n} (functions with edges: {len({k[0] for k in graph})}, total edges {len(graph)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
