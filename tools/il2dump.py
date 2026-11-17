"""Build a Ghidra dump list for a class group.
usage: il2dump.py <group> <spec>...   spec = Class | Class:subA|subB | Glob*   (case-insensitive; optional :filter = method name contains)
Writes ghidra/list_<group>.txt (lines "0xVA Class__method") and appends to tables/dump_groups.txt.
"""
import fnmatch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import il2names  # noqa: E402

ROOT = il2names.ROOT
SKIP_SUFFIX = ("SaveData", "SaveDataProxy", "Level", "SaveList")


def skip_class(cls):
    return "/" in cls or cls.endswith(SKIP_SUFFIX) or "<" in cls


def parse_spec(spec):
    pat, _, flt = spec.partition(":")
    return pat.lower(), [x.lower() for x in flt.split("|") if x]


def match(rows, spec):
    pat, flt = parse_spec(spec)
    out = []
    for va, nm, cls, meth, img in rows:
        if skip_class(cls) or not fnmatch.fnmatchcase(cls.lower(), pat):
            continue
        if flt and not any(f in meth.lower() for f in flt):
            continue
        out.append((va, nm, cls))
    return out


def build(group, specs):
    rows = il2names.name_rows([r for r in il2names.load_rows() if r[0] in il2names.IMAGES])
    seen, picked, used = set(), [], []
    for spec in specs:
        got = [x for x in match(rows, spec) if x[0] not in seen]
        seen.update(x[0] for x in got)
        picked += got
        used.append(f"{spec} -> {len({x[2] for x in got})} classes, {len(got)} methods")
    return picked, used


def main():
    group, specs = sys.argv[1], sys.argv[2:]
    picked, used = build(group, specs)
    with open(ROOT / "ghidra" / f"list_{group}.txt", "w", encoding="utf-8") as f:
        for va, nm, cls in picked:
            f.write(f"{va} {nm}\n")
    with open(ROOT / "tables" / "dump_groups.txt", "a", encoding="utf-8") as f:
        f.write(f"## {group}: {len(picked)} methods\n" + "\n".join(used) + "\n\n")
    print(group, len(picked), "methods")
    print("\n".join(used))


if __name__ == "__main__":
    main()
