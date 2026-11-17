"""Find Il2CppCodeGenModules in GameAssembly.dll, add method VA/RVA to methods.tsv."""
import mmap
import re
import struct
import sys
from pathlib import Path

DLL = r"F:\SteamLibrary\steamapps\common\TheLongDark\GameAssembly.dll"
TABLES = Path(__file__).resolve().parent.parent / "tables"


TAB = chr(9)
NL = chr(10)


class Pe:
    def __init__(self, buf):
        self.buf = buf
        pe = struct.unpack_from("<I", buf, 0x3C)[0]
        nsec = struct.unpack_from("<H", buf, pe + 6)[0]
        opt = struct.unpack_from("<H", buf, pe + 20)[0]
        self.base = struct.unpack_from("<Q", buf, pe + 24 + 24)[0]
        sec_off = pe + 24 + opt
        self.secs = []
        for i in range(nsec):
            nm, vs, va, rs, ro = struct.unpack_from("<8sIIII", buf, sec_off + i * 40)
            self.secs.append((nm.rstrip(b"\0").decode(), va, vs, ro, rs))

    def va_to_off(self, va):
        rva = va - self.base
        for _, sva, vs, ro, rs in self.secs:
            if sva <= rva < sva + min(vs, rs or vs):
                return ro + rva - sva
        return None

    def off_to_va(self, off):
        for _, sva, vs, ro, rs in self.secs:
            if ro <= off < ro + rs:
                return self.base + sva + off - ro
        return None

    def sec_of_va(self, va):
        rva = va - self.base
        for nm, sva, vs, _, _ in self.secs:
            if sva <= rva < sva + vs:
                return nm
        return None


def find_all(buf, pat):
    return [m.start() for m in re.finditer(re.escape(pat), buf)]


def module_candidates(pe, name):
    """Yield (struct offset, count, array va) for structs whose first ptr -> name string."""
    out = []
    for so in find_all(pe.buf, name.encode() + b"\0"):
        va = pe.off_to_va(so)
        if va is None:
            continue
        for ref in find_all(pe.buf, struct.pack("<Q", va)):
            cnt, pad, arr = struct.unpack_from("<IIQ", pe.buf, ref + 8)
            if 0 < cnt < 1_000_000 and pe.va_to_off(arr):
                out.append((ref, cnt, arr))
    return out


def read_array(pe, arr, cnt):
    off = pe.va_to_off(arr)
    return struct.unpack_from(f"<{cnt}Q", pe.buf, off)


def load_methods():
    with open(TABLES / "methods.tsv", encoding="utf-8") as f:
        head = f.readline().rstrip("\n").split("\t")
        rows = [l.rstrip("\n").split("\t") for l in f]
    return head, rows


def images_with_counts():
    counts = {}
    _, rows = load_methods()
    for r in rows:
        counts[r[0]] = counts.get(r[0], 0) + 1
    return counts


def ptr_table(pe, imgs):
    tables = {}
    for img in imgs:
        cands = module_candidates(pe, img)
        if not cands:
            continue
        ref, cnt, arr = max(cands, key=lambda c: c[1])
        tables[img] = read_array(pe, arr, cnt)
    return tables


def valid_va(pe, va):
    return va != 0 and pe.sec_of_va(va) in (".text", "il2cpp")


def resolve(pe, tables, r):
    tok = int(r[4], 16)
    tb = tables.get(r[0])
    idx = (tok & 0xFFFFFF) - 1
    if not tb or tok >> 24 != 6 or idx >= len(tb):
        return 0
    va = tb[idx]
    return va if valid_va(pe, va) else 0


def write_rows(head, out):
    with open(TABLES / "methods.tsv", "w", encoding="utf-8") as f:
        f.write(TAB.join(head[:7] + ["va", "rva"]) + NL)
        for r in out:
            f.write(TAB.join(r) + NL)


def sample_rows(pe, out):
    ac = [r for r in out if r[0] == "Assembly-CSharp.dll"]
    print("Assembly-CSharp", sum(1 for r in ac if r[7]), "of", len(ac))
    step = max(1, len(ac) // 10)
    for r in [x for x in ac if x[7]][::step][:10]:
        print(r[2], r[3], r[7], r[8], pe.sec_of_va(int(r[7], 16)))


def report(pe, tables, counts, out):
    mism = [(i, n, len(tables[i])) for i, n in counts.items() if i in tables and n != len(tables[i])]
    print("images with table", len(tables), "of", len(counts), "count mismatches", mism[:5])
    done = sum(1 for r in out if r[7])
    print("with address", done, "of", len(out), f"{100 * done / len(out):.1f}%")
    sample_rows(pe, out)


def main():
    pe = Pe(Path(DLL).read_bytes())
    counts = images_with_counts()
    tables = ptr_table(pe, counts)
    head, rows = load_methods()
    out = []
    for r in rows:
        va = resolve(pe, tables, r)
        out.append(r[:7] + ([f"0x{va:X}", f"0x{va - pe.base:X}"] if va else ["", ""]))
    write_rows(head, out)
    report(pe, tables, counts, out)


if __name__ == "__main__":
    main()
