# Network stream: native compiler failures

Cases of the network stream (`tests/network.neo.toml`) that the native
compiler (`neoc` of `chore/remove-python`) gets wrong. Commands run from the
repository root with `NEO_ROOT` set to it, on x86_64 Linux.

No case is left out: every fixture and driver of the stream builds and passes
with the native compiler.

## Worked around (no case left out)

Two type-checker gaps with `Ref<T>` values came up while writing the drivers.
Both were avoided by wrapping the `Ref` in a record; they are listed for the
compiler work after the merge. Not compared with the Python compiler.

### An `if` whose branches are `Ref<Socket>` loses the type

- Where: `tests/drivers/http_smoke.neo`, `hs_ask` (now builds an `HsSock`
  record in each branch instead).
- Reduced form:

  ```neo
  let socket=if s.open then s.socket else hs_open(arena,port,deadline).socket in
  socket_write(borrow_ref(socket),request,deadline)
  ```

- Command: `neoc check tests/drivers/http_smoke.neo`
- Error: `(error .../http_smoke.neo 125:27 borrow_ref requires Ref<T>)`

### Indexing an `Arr Ref<Socket> _` yields an empty type

- Where: a scratch probe while writing `hs_open_many`; the driver keeps
  `Arr HsSock _` (a record holding the `Ref`), which works.
- Reduced form:

  ```neo
  fn pick(borrow refs:Arr Ref<Socket> _, i:i64, none:Ref<Socket>) -> Ref<Socket>
    = if i>=0 && i<len(refs) then refs[i] else none
  ```

- Command: `neoc check probe.neo`
- Error: `(error probe.neo 8:5 body has type , declared Ref<Socket>)`
