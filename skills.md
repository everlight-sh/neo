# Writing Neo: a skill for coding agents

Neo is a language designed to be written by models. The compiler proves every
array index, division and range before the program runs, and reports what it
cannot prove as JSON. Work in a loop: write, check, fix, build. This file is the
whole skill; the full rules are in `docs/language-v01.md`.

## The loop

1. Write small functions with types and refinements on their inputs.
2. Run `neo check file.neo`. It prints JSON with one entry per proof obligation.
   A file without `main` is a library: check it with `neo check --library file.neo`.
3. For every obligation whose `status` is `"unproven"`, apply one of its `fixes`
   and check again. Repeat until `"ok": true`.
4. Build and run: `neo build file.neo -o app && ./app`, or `neo run file.neo`.

Never silence an unproven obligation by guessing. The compiler will not insert a
runtime check for you; an unproven index or division is a compile error.

## Reading `check` output

```json
{
  "fn": "at",
  "node": "0d1e7a0fe59c",
  "pos": [1, 42],
  "kind": "bounds",
  "goal": "0 <= i && i < len(a)",
  "status": "unproven",
  "counterexample": { "i": -1, "n": 0 },
  "fixes": [
    "guard: if 0 <= i && i < len(a) then … else …",
    "check 0 <= i && i < len(a) in …",
    "refine the index parameter, e.g. i : i64{0 <= i, i < n}"
  ]
}
```

- `kind`: `bounds` (array index), `division` (non-zero divisor), `range`,
  `precondition` (a caller must prove a callee's refinement), `invariant` (a loop
  state refinement, initially and preserved), `check` (an explicit runtime check).
- `goal`: what must hold at `pos` (line, column). `counterexample`: values that
  break it under what the compiler knows.
- `node`: a content hash of the expression. It does not change when you rename
  variables, so use it to track the same obligation across edits.
- `status`: `proven`, `checked` (kept as a runtime check because you wrote
  `check`), or `unproven` (a compile error).

Pick the fix that matches intent:

| Situation | Fix |
|---|---|
| The caller always passes a valid value | Refine the parameter: `i : i64{0 <= i, i < n}`; callers then get a `precondition` to prove |
| The value comes from input | Guard it: `if i >= 0 && i < len(a) then a[i] else 0` |
| Validity is known but not provable | `check cond in body`: a runtime check that traps if false |
| Loop variables | Give loop state a refinement: `loop (i : i64{i >= 0} = 0, ...)` |

## Syntax that matters

Everything is an expression. There are no statements and no early returns.

```neo
; Comments start with a semicolon.
fn square (x : i64) -> i64 = x * x

fn clamp (v : i64, lo : i64, hi : i64) -> i64
  = if v < lo then lo else if v > hi then hi else v

fn sum_to (n : i64{n >= 0}) -> i64
  = let total = sum(i in 0..n) i in total
```

- Types: `i64`, `i32`, `u8`, `f64`, `bool`, `unit`. Arrays: `Arr T n` where `n`
  names the length; `Arr u8 _` is an array of unknown length. A string literal
  is an `Arr u8 _`.
- Refinements: `i : i64{0 <= i, i < n}` (comma means "and"). They are checked at
  every call site.
- `let name = value in body` binds; bindings are immutable.
- Loops are expressions with explicit state:

```neo
fn starts_with (a : Arr u8 n, b : Arr u8 m) -> bool
  = m <= n && loop (i : i64{i >= 0} = 0, ok = true)
                while ok && i < m
                next (i + 1, a[i] == b[i])
                yield ok
```

  `next (...)` lists the new value of every state variable, in order; `yield`
  is the result.
- Comprehensions: `arr(i in 0..n) expr` builds an array, `sum(i in 0..n) expr`
  reduces. Both run in parallel and must be pure.
- Records: `type Body = { x : f64, m : f64 }`, built with `Body { x = 1.0, m = 2.0 }`,
  read with `b.x`, updated with `b with { x = 0.0 }`.
- Updating an array: `set(a, i, v)` returns the new array; it updates in place
  when `a` is not used again.
- Generics, enums and `match`, `Option<T>`/`Result<T,E>` and `let x = f()? in ...`
  are in `docs/language-v01.md`.

## Effects

Ordinary `fn` is pure: no I/O, and pure calls with literal arguments are
evaluated at compile time. Side effects need an effect function that names its
capabilities: `effect(fs, net) fn`. The capabilities are `fs`, `net`, `time`,
`env`, `process` and `unsafe`; calls check them transitively. Refinements and
comprehension bodies can never perform effects.

```neo
import "std:file"
effect(fs) fn main() -> unit
  = using file=open_file("/dev/null",0) in
    let status=file_status(file) in check status.ok in
    let result=read_file(file,32) in check result.ok in
    let output=print_out(concat("read ",int_text(len(result.value))," bytes\n")) in noop()
```

A `main` with no effects returns its output: `fn main () -> Arr u8 _ = "hi\n"`
prints it, and `fn main () -> i64 = 42` prints the number.

## Modules and the standard library

`import "helpers.neo"` loads a file relative to the current one; `import "std:json"`
loads the standard library. Declarations are public unless marked `private`.

| Module | Use it for |
|---|---|
| `std:strings` | Slicing, search, trimming, `int_text`, parsing, UTF-8 |
| `std:json` | `json_parse`, `json_get`, `json_int`, typed field decoding |
| `std:io`, `std:file` | Files, arguments, environment, clocks |
| `std:http`, `std:http_client` | Request and response helpers, HTTP client |
| `std:vec`, `std:hashmap`, `std:collections` | Growable vectors, maps, sorting |
| `std:option`, `std:result` | `Option<T>`, `Result<T,E>` |

An HTTP server is one call with a pure handler from request bytes to response
bytes:

```neo
fn handle (req : Arr u8 n) -> Arr u8 _
  = "HTTP/1.1 200 OK\r\nContent-Length: 13\r\n\r\nHello, World!"

effect fn main (port : i64{port > 0, port < 65536}) -> i64 = serve(port, handle)
```

## Pitfalls

- i64 arithmetic traps on overflow. Use `wrapping_add`, `wrapping_sub` or
  `wrapping_mul` only when wraparound is intended.
- Division needs a provably non-zero divisor: guard it or refine it.
- `next (...)` must list every loop state variable, in declaration order.
- Do not call effect functions from `fn`, from refinements or from inside `arr`/`sum`.
- Prefer refining parameters over sprinkling `check`: refinements are proven
  once and cost nothing at run time.

## Commands

| Command | Does |
|---|---|
| `neo check file.neo` | Type-check and prove; JSON on stdout |
| `neo check --library file.neo` | The same for a file without `main` |
| `neo build file.neo -o app` | Native binary (LLVM `-O3`; `--opt-level 0` for fast builds) |
| `neo run file.neo -- args` | Build and run |
| `neo test` | Project tests and `tests/*_test.neo` `test_*` functions |
| `neo fmt` | Format source files |
| `neo init dir` | New project with `neo.toml` |
| `neo lsp` | Language server |
| `neo doctor` | Check that Python, Clang and a linker are installed |

`install.sh` puts `neo` on your PATH; in a clone of the repository, run `./neo`.
