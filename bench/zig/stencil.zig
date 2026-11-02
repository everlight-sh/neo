// 3-point i64 stencil, `iters` passes, then a checksum; same algorithm as
// examples/stencil.neo and bench/rust/src/stencil.rs (ping-pong buffers, the
// output of each pass split across ZIG_THREADS workers).
const std = @import("std");
const par = @import("par.zig");

const Pass = struct { xs: []const i64, out: []i64 };

fn pass(p: Pass, lo: usize, hi: usize) void {
    const n = p.xs.len;
    for (lo..hi) |i| {
        p.out[i] = if (i == 0 or i + 1 == n) p.xs[i] else @rem(p.xs[i - 1] + 2 * p.xs[i] + p.xs[i + 1], 1000003);
    }
}

fn fill(xs: []i64, lo: usize, hi: usize) void {
    for (lo..hi) |i| xs[i] = @rem(@as(i64, @intCast(i)) * 2654435761, 1000003);
}

fn total(xs: []const i64, lo: usize, hi: usize) i64 {
    var acc: i64 = 0;
    for (xs[lo..hi]) |x| acc += x;
    return acc;
}

pub fn main(init: std.process.Init) !void {
    const args = try par.intArgs(init, 2, "stencil n iters");
    const n: usize = @intCast(args[0]);
    const workers = par.workerCount(init.environ_map);
    var a = try init.gpa.alloc(i64, n);
    defer init.gpa.free(a);
    var b = try init.gpa.alloc(i64, n);
    defer init.gpa.free(b);
    par.forRange(workers, n, a, fill);
    var k: i64 = 0;
    while (k < args[1]) : (k += 1) {
        par.forRange(workers, n, Pass{ .xs = a, .out = b }, pass);
        std.mem.swap([]i64, &a, &b);
    }
    try par.printLine(init.io, "{d}", .{par.sumRange(i64, workers, n, @as([]const i64, a), total)});
}
