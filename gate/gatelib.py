"""Shared parsing for gate.py / slim.py / callgraph.py: Ghidra C dumps -> functions, notes -> cites."""
import bisect
import re
from pathlib import Path

HDR = re.compile(r"^// ==== (\S+) @ ")
CAND = re.compile(r"^[A-Za-z_][^;{}=(]*\(")
IDENT = re.compile(r"[A-Za-z_]\w*")
KEYWORDS = {"if", "while", "for", "switch", "return", "else", "do", "sizeof"}
NUM = r"\d+(?:\s*[-–]\s*\d+)?"
LST = rf"{NUM}(?:\s*,\s*{NUM})*"
CITE = re.compile(rf"(?P<f>[\w.\-]+?\.c):\s*(?P<l>{LST})|\((?P<b>\s*{LST}\s*)\)")
FILTER = re.compile(r"^[\w.\-]+\.c(:\d+-\d+)?$")


def read_lines(path):
    return Path(path).read_text(encoding="utf-8", errors="replace").splitlines()


def headers_by_comment(lines):
    out = []
    for n, line in enumerate(lines, 1):
        m = HDR.match(line)
        if m:
            out.append((m.group(1), n))
    return out


def _sig_name(line):
    m = CAND.match(line)
    ids = IDENT.findall(line[:m.end() - 1]) if m else []
    return ids[-1] if ids and ids[-1] not in KEYWORDS else None


def _opens_body(lines, n):
    """True when a col-0 '{' follows line n (1-based) within a few lines, before any ';' or '}'."""
    for k in range(n - 1, min(n + 8, len(lines))):
        if lines[k] == "{":
            return True
        if ";" in lines[k] or lines[k].startswith("}"):
            return False
    return False


def headers_by_signature(lines):
    """Fallback for dumps without '// ==== name @' lines: col-0 C signature (may wrap over several
    lines) followed by a col-0 '{' line."""
    out = []
    for n, line in enumerate(lines, 1):
        name = _sig_name(line)
        if name and _opens_body(lines, n):
            out.append((name, n))
    return out


def parse_funcs(lines):
    """-> [(name, start, end)], 1-based inclusive; end = line before next header (EOF for the last)."""
    heads = headers_by_comment(lines) or headers_by_signature(lines)
    out = []
    for i, (name, start) in enumerate(heads):
        end = heads[i + 1][1] - 1 if i + 1 < len(heads) else len(lines)
        out.append((name, start, end))
    return out


class Dump:
    def __init__(self, path):
        self.path = Path(path)
        self.name = self.path.name
        self.lines = read_lines(path)
        self.funcs = parse_funcs(self.lines)
        self.starts = [f[1] for f in self.funcs]
        self.nonblank = [0]
        for t in self.lines:
            self.nonblank.append(self.nonblank[-1] + (1 if t.strip() else 0))

    def nb(self, a, b):
        """non-blank lines in [a, b], clipped to the file."""
        a, b = max(a, 1), min(b, len(self.lines))
        return self.nonblank[b] - self.nonblank[a - 1] if a <= b else 0

    def locate(self, line):
        i = bisect.bisect_right(self.starts, line) - 1
        return i if i >= 0 and line <= len(self.lines) else -1


def collect(paths, pattern="*.c"):
    out = []
    for p in map(Path, paths):
        out += sorted(p.rglob(pattern)) if p.is_dir() else [p]
    return out


def ranges(text):
    out = []
    for part in text.split(","):
        a = re.split(r"[-–]", part.strip())
        out.append((int(a[0]), int(a[-1])))
    return out


def parse_cites(text, label="notes"):
    """-> [(file name, a, b, 'label:line')]. A bare '(1-5, 9)' list belongs to the last named file
    of the same paragraph (a blank notes line resets it)."""
    out, last = [], None
    for ln, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            last = None
        for m in CITE.finditer(line):
            if m.group("f"):
                last, lst = m.group("f"), m.group("l")
            else:
                lst = m.group("b")
            if last:
                out += [(last, a, b, f"{label}:{ln}") for a, b in ranges(lst)]
    return out
