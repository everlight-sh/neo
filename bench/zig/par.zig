// Minimal data-parallel helpers for the Zig ports. Zig's standard library has
// no rayon-style parallel iterator, so this is the plain pattern a Zig program
// would use: spawn `workers - 1` threads (the caller is the last worker), let
// every worker claim chunks of [0, n) from one atomic counter, join.
// Like the Vif runtime, ranges under 1,024 elements run sequentially and work
// is cut into about `workers * 8` chunks. Threads are spawned per region; no
// persistent pool.
const std = @import("std");

pub const max_workers = 64;

/// ZIG_THREADS when set (the RAYON_NUM_THREADS / NEO_THREADS analogue),
/// otherwise the number of CPUs this process may run on.
pub fn workerCount(env: *const std.process.Environ.Map) usize {
    if (env.get("ZIG_THREADS")) |text| {
        const n = std.fmt.parseInt(usize, text, 10) catch 1;
        return std.math.clamp(n, 1, max_workers);
    }
    return std.math.clamp(std.Thread.getCpuCount() catch 1, 1, max_workers);
}

fn chunkSize(workers: usize, n: usize) usize {
    const chunks = workers * 8;
    return @max(1, (n + chunks - 1) / chunks);
}

/// Calls `body(ctx, lo, hi)` for disjoint chunks covering [0, n).
pub fn forRange(workers: usize, n: usize, ctx: anytype, comptime body: fn (@TypeOf(ctx), usize, usize) void) void {
    if (workers <= 1 or n < 1024) return body(ctx, 0, n);
    const Ctx = @TypeOf(ctx);
    const size = chunkSize(workers, n);
    var next = std.atomic.Value(usize).init(0);
    const Worker = struct {
        fn run(c: Ctx, counter: *std.atomic.Value(usize), total: usize, step: usize) void {
            while (true) {
                const lo = counter.fetchAdd(step, .monotonic);
                if (lo >= total) return;
                body(c, lo, @min(lo + step, total));
            }
        }
    };
    var threads: [max_workers]std.Thread = undefined;
    var spawned: usize = 0;
    while (spawned + 1 < workers) : (spawned += 1) {
        threads[spawned] = std.Thread.spawn(.{}, Worker.run, .{ ctx, &next, n, size }) catch break;
    }
    Worker.run(ctx, &next, n, size);
    for (threads[0..spawned]) |t| t.join();
}

/// Sum of `body(ctx, lo, hi)` over disjoint chunks covering [0, n). Each
/// worker accumulates locally; partials are added in worker order.
pub fn sumRange(comptime T: type, workers: usize, n: usize, ctx: anytype, comptime body: fn (@TypeOf(ctx), usize, usize) T) T {
    if (workers <= 1 or n < 1024) return body(ctx, 0, n);
    const Ctx = @TypeOf(ctx);
    const size = chunkSize(workers, n);
    var next = std.atomic.Value(usize).init(0);
    var partial: [max_workers]T = @splat(0);
    const Worker = struct {
        fn run(c: Ctx, counter: *std.atomic.Value(usize), total: usize, step: usize, out: *T) void {
            var acc: T = 0;
            while (true) {
                const lo = counter.fetchAdd(step, .monotonic);
                if (lo >= total) break;
                acc += body(c, lo, @min(lo + step, total));
            }
            out.* = acc;
        }
    };
    var threads: [max_workers]std.Thread = undefined;
    var spawned: usize = 0;
    while (spawned + 1 < workers) : (spawned += 1) {
        threads[spawned] = std.Thread.spawn(.{}, Worker.run, .{ ctx, &next, n, size, &partial[spawned + 1] }) catch break;
    }
    Worker.run(ctx, &next, n, size, &partial[0]);
    for (threads[0..spawned]) |t| t.join();
    var total: T = 0;
    for (partial[0 .. spawned + 1]) |p| total += p;
    return total;
}

/// Integer command-line arguments after the program name.
pub fn intArgs(init: std.process.Init, comptime count: usize, usage: []const u8) ![count]i64 {
    const args = try init.minimal.args.toSlice(init.arena.allocator());
    if (args.len != count + 1) {
        std.debug.print("usage: {s}\n", .{usage});
        std.process.exit(2);
    }
    var out: [count]i64 = undefined;
    for (&out, args[1..]) |*o, a| o.* = try std.fmt.parseInt(i64, a, 10);
    return out;
}

pub fn printLine(io: std.Io, comptime fmt: []const u8, args: anytype) !void {
    var buf: [128]u8 = undefined;
    // Streaming, not positional: a positional writer on a redirected regular
    // file writes at offset 0 instead of the shell's current offset.
    var w = std.Io.File.stdout().writerStreaming(io, &buf);
    try w.interface.print(fmt ++ "\n", args);
    try w.interface.flush();
}
