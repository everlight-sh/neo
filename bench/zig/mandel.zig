// Mandelbrot escape-time sum over a w x h grid; same algorithm as
// examples/mandel.neo and bench/rust/src/mandel.rs. Rows are split across
// ZIG_THREADS workers (see par.zig); columns are a plain loop.
const std = @import("std");
const par = @import("par.zig");

fn escape(cx: f64, cy: f64, max: i64) i64 {
    var zx: f64 = 0.0;
    var zy: f64 = 0.0;
    var k: i64 = 0;
    while (k < max and zx * zx + zy * zy <= 4.0) : (k += 1) {
        const nx = zx * zx - zy * zy + cx;
        zy = 2.0 * zx * zy + cy;
        zx = nx;
    }
    return k;
}

const Grid = struct { w: i64, h: i64, max: i64 };

fn rows(g: Grid, lo: usize, hi: usize) i64 {
    const w: f64 = @floatFromInt(g.w);
    const h: f64 = @floatFromInt(g.h);
    var acc: i64 = 0;
    for (lo..hi) |y| {
        const cy = -1.5 + 3.0 * @as(f64, @floatFromInt(y)) / h;
        var x: i64 = 0;
        while (x < g.w) : (x += 1) {
            acc += escape(-2.0 + 3.0 * @as(f64, @floatFromInt(x)) / w, cy, g.max);
        }
    }
    return acc;
}

pub fn main(init: std.process.Init) !void {
    const a = try par.intArgs(init, 3, "mandel w h max");
    const grid: Grid = .{ .w = a[0], .h = a[1], .max = a[2] };
    const total = par.sumRange(i64, par.workerCount(init.environ_map), @intCast(grid.h), grid, rows);
    try par.printLine(init.io, "{d}", .{total});
}
