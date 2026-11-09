# Bounded broadcast events

`std:events` is a C-free, HTTP-independent broadcast channel backend. Initialize
it once before forking workers:

```neo
let initialized=events_configure(16,128,4096) in
check initialized.ok in
let channel=event_channel("jobs") in
let published=event_publish(channel,"completed","{\"job\":42}",stamp) in
let batch=event_read(channel,0,4) in
...
```

Configuration selects maximum channels, retained messages per channel and JSON
payload bytes. Bounds are 1–64 channels, 1–1,024 messages and 64–8,192 bytes,
with the mapping capped at 64 MiB. Anonymous shared memory contains no private
heap pointers. The runtime preserves its mapping across `process_fork` and HTTP
worker forks. It lasts until the server family exits; it is not durable or
shared with independently launched processes.

Names are 1–48 ASCII alphanumeric bytes or `.`, `:`, `_`, `-`. Event names
starting `neokit-` are reserved for subscription control messages. Payloads are
validated JSON. `event_publish` returns the new monotonically increasing sequence
or an explicit error. `event_publish_once(channel,event,json,stamp,key)` ignores
positive producer keys no newer than the last committed producer key, returning
the current sequence without another publication. Use monotonically increasing
keys; `event_last_key` offers a cheap atomic producer check.

`event_read(channel,after,limit)` copies up to four messages after a cursor. Its
`EventBatch` reports an epoch, latest/oldest sequence, reset flag and typed
`EventMessage` values (`sequence`, `stamp`, `event`, `json`). Returned values are
independent copies: later ring overwrites do not mutate them. `event_latest`
returns at most the latest message. A cursor older than retention or ahead of
the channel returns a reset plus the latest available message. Applications
using incremental deltas must recover from an authoritative snapshot.

Short shared try-locks serialize registry changes and channel copy/publication.
They never wait: EAGAIN means retry later. No application callback executes
under a lock. A process crashing inside a locked operation leaves that channel
unavailable until restart; robust lock-owner recovery is outside this profile.
HTTP worker shutdown, ordinary task cancellation and subscriber disconnects do
not interrupt a locked operation, which contains only bounded synchronous work.

The generic `std:http_async` functions `http_async_response`,
`http_async_resume`, and `http_async_close` stream byte responses through short
event/timer callbacks, with owned captures, disconnect cleanup and shutdown deadlines.
Callbacks may emit at most 48 KiB per turn and must return promptly without
blocking waits. They allocate no fiber stack. Socket/database waits belong in
ordinary cooperative tasks, which can publish when their I/O completes.

`std:sse` contains both incremental SSE decoding and the shared server encoder.
The optional HTTP-server package imports this encoder instead of maintaining a
second protocol implementation. NeoKit builds channel authorization, stream
routes and browser subscriptions on these reusable primitives.

`tests/fixtures/events.neo` checks fork sharing, byte/value isolation, deduplication,
rollover/reset and UTF-8 framing. NeoKit's independent protocol tests exercise
HTTP authentication, framing, replay, heartbeat, cancellation, backpressure and
graceful shutdown on macOS and static ARM64 Linux.

## Publish-triggered delivery

`event_watch(channel, sequence)` arms the current short HTTP continuation against
that channel version. Publication commits the ring, releases the lock, and signals
the pre-fork worker notification sockets. The HTTP executor dispatches changed
subscriptions when those sockets become readable. Registering after a racing
publication marks the continuation ready immediately. `event_watch_unlock` is
used after read contention; the lock owner wakes registered waiters on release.
No periodic timer reads the channel. Timer deadlines are reserved for heartbeat
and connection renewal; neither requires a data read.

Pending output resumes through socket write readiness. The continuation's cached
HTTP slot is revalidated after Linux compaction, preventing a moved connection
from using its old slot. `event_read_count` and `http_async_callback_count` provide
process-local diagnostics for idle/wakeup tests.

`std:timer` supplies bounded process-owned interval callbacks. An interval started
before HTTP forks runs only in the original worker; children forget its private
registry. The HTTP executor drives it, or a standalone program can use
`timer_poll`. These timers produce application data independently of subscribers;
they are not subscription polling. Stop explicit timer handles with
`timer_interval_stop`; HTTP shutdown stops all intervals before draining.
There are at most 16 intervals per process, each with a copied capture of at
most 16 KiB and an interval from 1 ms to 24 hours. They coalesce missed ticks
and do not overlap callback execution. `timer_poll(0..120000)` supports a
standalone event loop. These callbacks must remain short and nonblocking;
cooperative tasks handle database/network waits and publish their completed work.

## Prepared event streams and retained continuation state

`std:event_stream` composes the existing event bus, SSE encoder and short HTTP
continuations. `event_stream_frame(channel, epoch, message)` returns a prepared
HTTP chunk for the event, with the same `epoch.sequence` cursor. Encoding is
cached per worker; keys include the channel, epoch, sequence and exact event/data
bytes. A miss validates/encodes the frame, while another subscriber can reuse
it. Evicted replay entries are encoded again when needed.

`std:http_async` provides these independently reusable foundations:

- `HttpAsyncState` contains eight `i64` words owned by a callback. Get/set it with
  `http_async_state_get/set`; the words survive callback turns and start at zero
  on admission/slot reuse. They do not serialize through the byte capture.
  This is fixed scalar state, not arbitrary heap-record capture. The existing
  owned byte capture remains available for immutable application data.
- `http_async_prepare(bytes)` creates an opaque `HttpAsyncFrame` with bounded
  chunk framing. Its payload may contain up to 49,152 bytes.
- `http_async_frame_find/remember` maintain at most 64 prepared frames per
  process. A key has a numeric namespace/version/epoch and two exact byte keys
  totaling at most 16 KiB. Wire bytes are limited to 49,184 per entry. Use a
  distinct application namespace; positive channel IDs are used by the event
  adapter. Remembering an already cached frame returns that reference unchanged.
  The cache is bounded live storage; allocator rounding/free-block retention
  can exceed the sum of logical entry lengths.
- `http_async_send_frame(frame, wake)` is returned directly from a short
  callback. It writes the immutable frame synchronously without allocating an
  intermediate response packet. A partial/would-block write copies the unsent
  suffix into connection-owned storage before returning. Socket readiness then
  drives output, preserving the existing output/deadline bounds.
- Cached frames use PID/generation-checked tokens. An evicted token or a token
  inherited by a child cannot access a reused allocation; sending it closes
  safely. Use `http_async_frame_valid` to check a retained token, or
  `http_async_frame_payload` to obtain an owned copy that survives eviction.
  Callbacks must not yield or block while preparing/sending a frame.
- `http_async_send_bytes` combines preparation and a direct send for uncommon
  output. Existing `http_async_yield/resume/finish/close` packets still work;
  return exactly one send/result per callback turn.

Callback admission/removal now uses a free list and a dense active vector.
Tick/timeout processing walks active callbacks instead of all 2,048 capacity
slots. Swap removal keeps the moved callback's position correct; connection
ownership is still revalidated after Linux compaction. Empty legacy captures
are retained without a new allocation on every turn.

`tests/fixtures/prepared_frames.neo` verifies keys, bounded storage, value
isolation, eviction/generation checks and fork ownership. The independent
`tests/prepared_frames.py` peer checks retained state/slot reset, direct writes,
a callback whose next wake passes during its own work, four backpressured
4 MiB responses across eviction, responsive fast requests and
disconnect/shutdown cleanup with one and two workers.
