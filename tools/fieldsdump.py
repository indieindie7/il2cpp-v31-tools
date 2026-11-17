"""fieldsdump.py: field names per type in declaration order -> tables/fields.tsv (class, n, field).
For enums the first field is value__; member values are NOT read (order only). usage: py -3.13 fieldsdump.py"""
import il2meta as m

def main():
    data, sec = m.load()
    name, images, types, methods, fields = m.build(data, sec)
    with open(m.OUT / "fields.tsv", "w", encoding="utf-8") as f:
        for t in types:
            cls = name(t[0])
            for k in range(t[18]):
                f.write("%s\t%d\t%s\n" % (cls, k, name(fields[t[8] + k][0])))

main()
