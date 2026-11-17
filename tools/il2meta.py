"""Parse IL2CPP metadata v31 -> tables/types.tsv, tables/methods.tsv."""
import struct
import sys
from pathlib import Path

META = r"F:\SteamLibrary\steamapps\common\TheLongDark\tld_Data\il2cpp_data\Metadata\global-metadata.dat"
OUT = Path(__file__).resolve().parent.parent / "tables"

# header slot index (after magic, version) -> name
SECTIONS = ["strlit", "strlitdata", "string", "events", "properties", "methods",
            "pdefaults", "fdefaults", "defdata", "marshal", "parameters", "fields",
            "gparams", "gconstraints", "gcontainers", "nested", "interfaces",
            "vtable", "ifoffsets", "typedefs", "images", "assemblies"]
SIZES = {"typedefs": 88, "methods": 36, "fields": 12, "images": 40, "parameters": 12}


def load(path=META):
    data = Path(path).read_bytes()
    magic, ver = struct.unpack_from("<iI", data, 0)
    if magic & 0xFFFFFFFF != 0xFAB11BAF or ver != 31:
        raise SystemExit("bad metadata magic/version")
    sec = {}
    for i, name in enumerate(SECTIONS):
        sec[name] = struct.unpack_from("<ii", data, 8 + i * 8)
    return data, sec


def check_sizes(sec):
    for name, rec in SIZES.items():
        off, size = sec[name]
        if size % rec:
            raise SystemExit(f"{name}: size {size} not divisible by {rec}")


def read_string(data, base, idx):
    start = base + idx
    return data[start:data.index(b"\0", start)].decode("utf-8", "replace")


def records(data, sec, name, fmt):
    off, size = sec[name]
    rec = struct.calcsize(fmt)
    return [struct.unpack_from(fmt, data, off + i * rec) for i in range(size // rec)]


# typedef: name ns byval declaring parent elem gcont flags fstart mstart estart pstart nstart istart vstart iostart
#          mcount pcount fcount ecount ncount vcount icount iocount bitfield token
TYPE_FMT = "<7iI8i8HII"
METHOD_FMT = "<7i4H"
IMAGE_FMT = "<10i"
FIELD_FMT = "<3i"


def build(data, sec):
    sbase = sec["string"][0]
    name = lambda i: read_string(data, sbase, i)
    images = records(data, sec, "images", IMAGE_FMT)
    types = records(data, sec, "typedefs", TYPE_FMT)
    methods = records(data, sec, "methods", METHOD_FMT)
    fields = records(data, sec, "fields", FIELD_FMT)
    return name, images, types, methods, fields


OUTER = {}


def map_nested(data, sec, types):
    off = sec["nested"][0]
    for i, t in enumerate(types):
        for k in range(t[20]):
            OUTER[struct.unpack_from("<i", data, off + (t[12] + k) * 4)[0]] = i


def type_full(name, types, i, cache):
    if i in cache:
        return cache[i]
    t = types[i]
    base = name(t[0])
    d = OUTER.get(i, -1)
    if d >= 0:
        base = type_full(name, types, d, cache)[1] + "/" + base
        res = (name(t[1]) or type_full(name, types, d, cache)[0], base)
    else:
        res = (name(t[1]), base)
    cache[i] = res
    return res


def write_types(name, images, types, fields, cache, out):
    out.write("idx\timage\tnamespace\tclass\tparent\tmethodStart\tmethodCount\tfieldStart\tfieldCount\ttoken\n")
    for im in images:
        for i in range(im[2], im[2] + im[3]):
            t = types[i]
            ns, cls = type_full(name, types, i, cache)
            parent = type_full(name, types, t[4], cache)[1] if 0 <= t[4] < len(types) else ""
            out.write(f"{i}\t{name(im[0])}\t{ns}\t{cls}\t{parent}\t{t[9]}\t")
            out.write(f"{t[16]}\t{t[8]}\t{t[18]}\t0x{t[-1]:08X}\n")


def method_rows(name, images, types, methods, cache):
    rows = []
    for im in images:
        for i in range(im[2], im[2] + im[3]):
            t = types[i]
            ns, cls = type_full(name, types, i, cache)
            for m in range(t[9], t[9] + t[16]):
                md = methods[m]
                rows.append((name(im[0]), ns, cls, name(md[0]), md[6], md[10], m))
    return rows


def main():
    data, sec = load()
    check_sizes(sec)
    name, images, types, methods, fields = build(data, sec)
    cache = {}
    map_nested(data, sec, types)
    OUT.mkdir(exist_ok=True)
    with open(OUT / "types.tsv", "w", encoding="utf-8") as f:
        write_types(name, images, types, fields, cache, f)
    rows = method_rows(name, images, types, methods, cache)
    with open(OUT / "methods.tsv", "w", encoding="utf-8") as f:
        f.write("image\tnamespace\tclass\tmethod\ttoken\tparams\tmidx\n")
        for r in rows:
            f.write(f"{r[0]}\t{r[1]}\t{r[2]}\t{r[3]}\t0x{r[4]:08X}\t{r[5]}\t{r[6]}\n")
    print("images", len(images), "types", len(types), "methods", len(methods), "fields", len(fields))
    for im in images:
        print(name(im[0]), im[2], im[3])
    bad = sum(1 for r in rows if (r[4] >> 24) != 6 and r[4] != 0)
    print("method rows", len(rows), "tokens not 0x06:", bad)
    names = {c[1] for c in cache.values()}
    for k in ("Condition", "Hunger", "Thirst", "Fatigue", "Freezing", "BaseAi", "Wolf"):
        print(k, k in names)


if __name__ == "__main__":
    main()
