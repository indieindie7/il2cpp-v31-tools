"""citecheck.py: check every `file:line` reference of a notes file against the source by content.
usage: py -3.13 -I citecheck.py <notes.md> <source root> <out.md> [window=4] [full=1]
full > 1 = review table: every reference with its claim and up to <full> cited source lines.
Per reference: the claim line, the cited source lines, and a score = share of the claim's code words
(backticked words, CAPS_NAMES, snake_case names, numbers) found within +-window lines of the cite.
Score 0 with code words present = suspect; references without code words = "manual".
"""
import io, os, re, sys

N = chr(10)
FULL = 1  # argv[5]: print up to this many cited source lines per reference (review table for a reader)
CITE = re.compile(r"((?:[A-Za-z_0-9]+/)*[A-Za-z_0-9]+\.(?:cs|scm|prolog|c)):(\d+)(?:-(\d+))?")
WORD = re.compile(r"`([^`]+)`|\b([A-Z][A-Z0-9_]{3,})\b|\b([a-z]+_[a-z0-9_]+)\b|(?<![\w.:])(\d+(?:\.\d+)?)(?![\w.:])")


def index(root):
    idx = {}
    for r, d, fs in os.walk(root):
        for f in fs:
            idx.setdefault(f, []).append(os.path.join(r, f))
    return idx


def find(idx, ref):
    c = idx.get(ref.split("/")[-1], [])
    want = ref.replace("/", os.sep)
    for p in c:
        if p.endswith(want): return p
    return c[0] if c else None


def words(claim):
    out = set()
    for m in WORD.finditer(CITE.sub(" ", claim)):
        w = next(g for g in m.groups() if g)
        for part in re.split(r"[^A-Za-z0-9_.]+", w):
            if len(part) >= 2 and not CITE.match(part + ":1"): out.add(part.lower())
    return out


def load(p, cache):
    if p not in cache: cache[p] = io.open(p, encoding="utf-8", errors="replace").read().split(N)
    return cache[p]


def check(m, ws, idx, cache, win):
    """-> (kind, text); kind = missing | manual | suspect | ok"""
    p = find(idx, m.group(1))
    if not p: return "missing", "NO FILE"
    src = load(p, cache)
    a = int(m.group(2)); b = int(m.group(3) or a)
    if a > len(src): return "missing", "OUT OF RANGE (%d lines)" % len(src)
    ctx = N.join(src[max(0, a - 1 - win):min(len(src), b + win)]).lower()
    hit = [w for w in ws if w in ctx]
    kind = "manual" if not ws else ("ok" if hit else "suspect")
    tag = "ok %d/%d" % (len(hit), len(ws)) if kind == "ok" else kind.upper()
    return kind, "[%s]" % tag + quote(src, a, b)


def quote(src, a, b):
    if FULL <= 1: return " src: " + src[a - 1].strip()[:110]
    body = [l.rstrip()[:130] for l in src[a - 1:min(b, a + FULL - 1)] if l.strip()]
    if b - a + 1 > FULL: body.append("... (%d more lines)" % (b - a + 1 - FULL))
    return "".join(N + "    | " + l for l in body)


def main():
    notes, root, out = sys.argv[1:4]
    win = int(sys.argv[4]) if len(sys.argv) > 4 else 4
    global FULL
    FULL = int(sys.argv[5]) if len(sys.argv) > 5 else 1
    idx = index(root); cache = {}; rows = []
    cnt = {"missing": 0, "manual": 0, "suspect": 0, "ok": 0}
    for ln, claim in enumerate(io.open(notes, encoding="utf-8"), 1):
        ws = words(claim)
        for m in CITE.finditer(claim):
            kind, text = check(m, ws, idx, cache, win)
            cnt[kind] += 1
            rows.append("- L%d %s %s" % (ln, m.group(0), text))
            if kind != "ok" or FULL > 1: rows.append("  claim: " + claim.strip()[:(600 if FULL > 1 else 200)])
    head = "# citecheck %s: %d refs, %d missing, %d suspect, %d manual" % (
        os.path.basename(notes), sum(cnt.values()), cnt["missing"], cnt["suspect"], cnt["manual"])
    io.open(out, "w", encoding="utf-8", newline=N).write(N.join([head] + rows) + N)
    print(head)


main()
