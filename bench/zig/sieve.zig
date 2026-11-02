// Sieve of Eratosthenes over 0..n, in place, one byte per flag; same
// algorithm as examples/sieve.neo. Marking is sequential (as in Vif); the
// initial fill and the final count are split across ZIG_THREADS workers,
// mirroring Vif's parallel `arr`/`sum`.
const std = @import("std");
const par = @import("par.zig");

fn fill(marks: []bool, lo: usize, hi: usize) void {
    for (lo..hi) |k| marks[k] = k >= 2;
}

fn count(marks: []const bool, lo: usize, hi: usize) i64 {
    var acc: i64 = 0;
    for (marks[lo..hi]) |m| acc += @intFromBool(m);
    return acc;
}

pub fn main(init: std.process.Init) !void {
    const args = try par.intArgs(init, 1, "sieve n");
    const n: usize = @intCast(args[0]);
    const workers = par.workerCount(init.environ_map);
    const marks = try init.gpa.alloc(bool, n + 1);
    defer init.gpa.free(marks);
    par.forRange(workers, n + 1, marks, fill);
    var i: usize = 2;
    while (i <= n and i * i <= n) : (i += 1) {
        if (marks[i]) {
            var j = i * i;
            while (j <= n) : (j += i) marks[j] = false;
        }
    }
    try par.printLine(init.io, "{d}", .{par.sumRange(i64, workers, n + 1, @as([]const bool, marks), count)});
}
