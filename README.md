# il2cpp-v31-tools

Small Python + Ghidra scripts to read a Unity IL2CPP game (metadata version 31, Windows x64) for private study.
No external downloads, no game files here. You need your own copy of the game.

Tested on one game (The Long Dark, Steam). Nothing from the game is in this repo: no binaries, no tables, no dumps, no decompiled code.

## What each tool does
| File | Job |
|---|---|
| `tools/il2meta.py` | parse `global-metadata.dat` -> `tables/types.tsv`, `tables/methods.tsv` |
| `tools/il2ptr.py` | find `Il2CppCodeGenModules` in `GameAssembly.dll`, add method addresses to `methods.tsv` |
| `tools/fieldsdump.py` | `tables/fields.tsv`: class, index, field name (enum members too) |
| `tools/il2names.py` | write `ghidra/names.txt` (`0xVA Class__Method`) |
| `ghidra_scripts/NameFuncs.java` | create + rename functions in Ghidra from `names.txt` |
| `tools/il2dump.py` | make a method list for a group of classes (name, glob, or `Class:filter`) |
| `ghidra_scripts/DumpList.java` | decompile that list to one C file |
| `tools/il2split.py` | split the C dump into one file per class |
| `tools/citecheck.py` | check `File.c:line` cites in a notes file against the dumps |
| `gate/` | generic read-loop gate for any Ghidra C dump: `gate.py` (every function needs a note cite, depth rule), `slim.py`, `callgraph.py`; see `gate/README.md` |

## Use
1. Edit `META` in `il2meta.py` and `DLL` in `il2ptr.py` to your game paths.
2. `py il2meta.py`, `py il2ptr.py`, `py fieldsdump.py`, `py il2names.py all`
3. Import `GameAssembly.dll` in Ghidra with `-noanalysis`, run `NameFuncs.java names.txt`.
4. `py il2dump.py mygroup Hunger "PlayerManager:Sprint|Stamina" Feat*`, then headless `DumpList.java dump_mygroup.c list_mygroup.txt`, then `py il2split.py mygroup`.

## Limits
- Metadata v31 only, plain (not encrypted) metadata.
- Tuning values set in the Unity inspector are prefab data, not code: the dumps show field offsets, not values.
- No method signatures, no string literal names; methods that share a stub address get no name.
- Enum member values are not read (order only).

Research and personal study only. Do not publish game binaries, data or decompiled code.
