# Language stream: native compiler gaps

Cases from the language scripts that the Python compiler handled and the
native compiler (`neoc` of `chore/remove-python`) does not. They are left out
of `tests/language.neo.toml`. Commands run from the repository root with
`NEO_ROOT` set to it, on x86_64 Linux.

## 1. Else-if chains are not lowered to a switch

- Scripts: `opcode_vm.py` (one `switch i64` with at least 39 cases in `step`),
  `deep_dispatch.py` (a 300-case switch in the build report),
  `test_switch_dispatch.py` (40-arm chains, match on fields and bytes, grouped
  arms, chains that switch on the first scalar only).
- Command: `neoc build tests/fixtures/opcode_vm.neo --emit-llvm`, then look at
  the function after `; fn __m…_step`.
- What happened: `step` has 39 `icmp eq` comparisons and no `switch`. The
  module's only `switch` is the width dispatch inside the runtime helper
  `@neo.bytes.read`. `deep_dispatch.neo` has 341 `icmp eq` and the same single
  runtime `switch`. `neoc build --report` has no `switches` field to check
  against.
- Ported anyway: both fixtures' results (the `opcode-vm` and `deep-dispatch`
  cases) and the 300-arm proof. Only the lowering check is missing.

## 2. push growth of nested arrays and record arrays

- Script: `push_boundaries.py`, modes 4 (nested `Arr Arr u8`, 24-byte
  elements) and 5 (records stored as structure-of-arrays planes), built with
  `NEO_ALLOC_STATS=1`.
- Command: `NEO_ALLOC_STATS=1 neoc build tests/fixtures/push_boundaries.neo -o pb`
  followed by `./pb 4 1`, `./pb 4 2`, `./pb 5 1`, `./pb 5 2`.
- What happened: the output is `checksum requests bytes`. Checksums match;
  allocation requests or bytes do not match the script's model:

  | run | native | script's model |
  |---|---|---|
  | `4 1` | `7 1 64` | `7 1 24` |
  | `4 2` | `14 2 160` | `14 2 72` |
  | `5 1` | `0 1 48` | `0 1 16` |
  | `5 2` | `8 1 48` | `8 2 48` |

  Natively, nested arrays reserve more than one element's descriptor, and
  record planes grow geometrically where the model expected one exact
  allocation per push. This may be an intended policy rather than a bug, but
  the model must be updated before these modes can be checked again.
- Ported anyway: modes 0-3 (`push-boundaries`, 308 runs through 1M elements).

## 6. JSON writer growth is linear in requests and quadratic in bytes

- Script: `json_writer_growth.py`. It requires at most 128 allocation requests
  for integer arrays and reused fragments (2n+128 for object rows), and at
  most 512n+65536 requested bytes.
- Command: `NEO_ALLOC_STATS=1 neoc build tests/fixtures/json_writer_growth.neo -o w`,
  then `./w MODE N`. The first output line is `requests bytes`.
- What happened (the same with 1 and 4 workers):

  | run | requests | requested bytes | bounds |
  |---|---|---|---|
  | `0 1000` | 1018 | 1,898,374 | 128, 577,536 |
  | `1 1000` | 4024 | 35,714,347 | 2128, 577,536 |
  | `2 1000` | 1024 | 11,023,225 | 128, 577,536 |
  | `3 1000` | 3024 | 12,084,196 | 2128, 577,536 |
  | `0 100000` | 100,024 | 28,939,704,012 | 128, 51,265,536 |
  | `1 100000` | 400,028 | 386,819,036,903 | 200,128, 51,265,536 |

  So the output buffer is reallocated once per value instead of growing
  geometrically. `./w 1 100000` takes 13.4 s on the box; mode 0 takes 1.0 s.
- Ported anyway: the outputs are complete and ordered at 1k and 10k, in all
  four modes, with 1 and 4 workers (`json-writer-growth`).
