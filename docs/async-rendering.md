# Cooperative tasks and HTTP streaming

`std:async` provides reusable byte-result tasks independently of NeoKit. A task
keeps its ordinary Neo call stack while a native socket wait yields to its
executor. HTTP, verified HTTPS, DNS, TCP/UDP and the shared PostgreSQL client use
the same socket wait boundary. They need no separate async protocol clients.
There is no embedded JavaScript engine, worker thread pool or libc dependency.

```neo
import "std:async"
import "std:http_client"

private effect(fs,net,env,time,process) fn fetch(path:Arr u8 n)->Arr u8 _
  = let response=http_request("127.0.0.1",8080,"GET",path,"",2000,1048576) in
    if response.ok then response.body else let failed=async_fail(5) in ""

effect fn main()->i64
  = let deadline=deadline_after(3000) in
    using first=async_bytes(function(fetch),"/first",deadline.value) in
    using second=async_bytes(function(fetch),"/second",deadline.value) in
    let a=async_bytes_await(first,deadline.value) in
    let b=async_bytes_await(second,deadline.value) in
    if a.ok && b.ok then 0 else 1
```

Callbacks receive copied byte captures and return bytes. Tasks are scoped
resources; unfinished owners cancel and detach when dropped. Cancellation
resumes the normal call stack so `using` cleanup runs. HTTP executors pump these
detached tasks automatically. Standalone programs that drop unfinished tasks
must subsequently call `async_drain(deadline)` outside the task to complete
cleanup. `async_drain` is intended for detached cleanup; completed tasks whose
owners are still live remain counted until their owners are dropped.

`async_bytes_await` returns a `BytesResult`; admission, cancellation, timeout and
callback failure are explicit errors. `async_fail(code)` marks failure without
trapping. `async_cancelled`, `async_yield` and `async_checkpoint` support custom
cooperative work. Deadlines are absolute monotonic milliseconds, at most 120 s
ahead. A cancelled callback must return promptly; cancellation does not kill a
CPU-bound loop. Socket operations also check cancellation and checkpoint.

## HTTP composition

Enable `http_server_options(grace_ms,true)` before `serve_effect` and import
`std:http_async`. The existing kqueue/epoll worker multiplexes client sockets,
outbound readiness and deadlines.

- `http_response_async(capture,callback,deadline)` schedules a complete buffered
  HTTP response. Return its successful value (an empty internal placeholder)
  directly from the handler. The callback returns `web_encode_close(...)` wire
  bytes. Failures before headers return 503, or 504 for a render deadline. Both
  carry `web_encode`'s security headers; the 503 is dated when the response is
  admitted.
- `http_deferred` and `http_render_start` admit independent callbacks before
  returning chunked headers and the initial shell. `http_deferred_frame` wraps
  each result in an atomic prefix/body/suffix or a safe error fragment.
  `http_render_start_with_tail` appends a final HTML footer.
- The streamed head has `web_encode`'s defaults (`Cache-Control: no-store`,
  nosniff and the default Content-Security-Policy). `http_render_start_at`,
  `http_render_start_with_tail_at` and `http_async_start_at` take two more
  arguments: `headers` and `stamp`. `headers` holds extra header lines,
  `"Name: value\r\n"` each, as `web_with_header` writes them. A
  Cache-Control, Content-Security-Policy or Date line there replaces the
  default. `stamp` (Unix ms, or -1 for none) adds a Date header. Header lines
  get the same checks as `web_with_header` (at most 8 KiB in all, no
  Content-Length, Transfer-Encoding, Connection or Content-Type). An invalid
  line fails the start with error 22 before anything is admitted.
- A buffered response callback can first wait for auth/database/network work,
  then return `http_render_start(...)` headers. Its child callbacks remain queued
  until those headers have been enqueued. Partial admission rolls back before
  any shell is committed.
- Raw deferred callbacks may call `http_render_write(web_html(bytes))` repeatedly
  and return their final bytes. Stop after a failed write. Framed callbacks
  return one complete HTML fragment and cannot also use raw writes.

Userland pending response output is bounded at 64 KiB per connection and emitted
in chunks of at most 16 KiB. Backpressure suspends the writer. A group writer
lock prevents one fragment's envelope being interleaved with another. Completion
waits for the userland queue to drain or its deadline. Disconnects cancel all
attached tasks, including while an upstream has sent no bytes. SIGTERM stops
accepting, drains until the configured grace deadline, then cancels outstanding
work. This HTTP/1.1 streaming profile closes the connection after completion;
client EOF/half-close cancels an async response.

## Bounds and limits

There are at most 256 live tasks per worker and 32 deferred tasks per response.
Each task reserves a guarded 1 MiB stack (plus two 64 KiB guard regions).
Captures are limited to 16 MiB plus a 16 KiB request-header allowance per task;
results to 4 MiB; aggregate logical copied captures and aggregate results each
to 64 MiB per worker. Envelopes and footers have separate 16 KiB bounds. These
are admission bounds, not a bound on total application or process RSS. Stack
mappings and copied buffers are released when owners/groups finish. Inspect
`async_stats()` for live/waiting/completed tasks and logical capture/result bytes.

Scheduling is cooperative. Regular file reads, writes and `fsync` remain
synchronous; contended advisory `file_lock` waits retry nonblocking and yield.
Database result sets are still buffered by their protocol library; this is
concurrent query waiting, not a PostgreSQL cursor/row-streaming API. There is no
general async language syntax, arbitrary closure capture, preemptive scheduling
or resumable traps. Pure CPU work must yield explicitly. An HTTP worker resumes
at most eight tasks between socket waits and stops a batch once it has run for a
millisecond, so one task that holds the CPU delays other requests by its own
run time, not by the tasks queued behind it.

Native tests cover nested tasks, contended file locks, delayed HTTP/TLS/DNS,
timeouts, repeated handle reuse, backpressure, cancellation, admission rollback,
header handoff and graceful shutdown. See the `async-tasks`, `async-protocols`,
`async-pressure` and `http-async` cases in `tests/network.neo.toml`.
