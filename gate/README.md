# decomp read-loop gate (generic)

Works on any Ghidra C dump (one big .c or a folder of .c; names FUN_xxx, hand names, Class__Method). Python 3, no dependencies.
Functions come from `// ==== NAME @ addr` header lines; if a file has none, col-0 C signatures followed by a col-0 `{` are used
(wrapped signatures ok; failed decompiles without a signature are invisible in that mode).

- `gate.py <tag> --dumps <dir|file.c>... --notes <file|dir>... [--min-lines 12] [--trivial-name RE] [--profile il2cpp] [--after-header] [--bucket 200] [File.c[:A-B]...]`
  Prints `File.c:start<TAB>N lines<TAB>name` for every non-trivial function with no valid cite, then `UNREAD n`; exit 1 while n > 0, exit 2 when no function was parsed.
  Trivial = function span (header line to next header) < `--min-lines`; `--profile il2cpp` adds ctor/cctor/Serialize/Deserialize/get_/set_ rules.
  Cites: `File.c:A-B`, `File.c:N`, `File.c:1-5, 9`, bare `(7-9)` after a named file in the same paragraph. File match is by basename, case-insensitive.
- `slim.py <dump>... [--out DIR] [--profile il2cpp] [--drop RE]` numbered `N: text` reading copies (N = real dump line). Default drops blank lines, lone braces, local declarations. Never point the gate at slim copies.
- `callgraph.py callers|callees|table NAME|ALL --dumps ...` text-only edges: `B(` = call, `PTR_B` = ptr, other mention = ref. Comments and the function's own signature are ignored. Indirect calls via DAT_/PTR_ to undefined targets are not resolved.

## Strict cite rule
A function is READ only if ONE cite lies wholly inside it (header line to last line before next header) and holds at least one non-blank line below the header.
Not counted, listed as `BADCITE` (warning, never changes exit code): `span` (crosses a function boundary: split it per function), `header-only` (header or blank lines only),
`outside` (past EOF), `unknown file`, `reversed`. `--after-header` additionally requires the cite to start below the header line.

## Depth rule
`--bucket N` (default 200, 0 = off): a function longer than N lines counts as read only when its cites touch at least half of its N-line slices. Stops a 1000-line function passing on one cite of its first lines.

## Test
`py -3 tests/test_depth.py` builds a synthetic 500-line function (no game content) and checks the depth rule and the exit codes.

Use: write notes while reading, run the gate, read what it lists, repeat until `UNREAD 0`.
