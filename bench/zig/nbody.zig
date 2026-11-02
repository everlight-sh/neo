// N-body, same model and initial conditions as examples/nbody.neo and
// bench/rust/src/nbody.rs: array of structs, softening 0.01, dt 0.001,
// kick then drift each step, then total energy. Bodies are split across
// ZIG_THREADS workers; the inner loops are plain sequential sums.
const std = @import("std");
const par = @import("par.zig");

pub const Body = struct { x: f64, y: f64, z: f64, vx: f64, vy: f64, vz: f64, m: f64 };

pub fn init(bs: []Body) void {
    const n: f64 = @floatFromInt(bs.len);
    for (bs, 0..) |*b, k| {
        const i: i64 = @intCast(k);
        b.* = .{
            .x = @as(f64, @floatFromInt(@rem(i * 2654435761, 1009))) / 1009.0,
            .y = @as(f64, @floatFromInt(@rem(i * 40503, 1013))) / 1013.0,
            .z = @as(f64, @floatFromInt(@rem(i * 69069, 1019))) / 1019.0,
            .vx = 0.0, .vy = 0.0, .vz = 0.0, .m = 1.0 / n,
        };
    }
}

const Step = struct { src: []const Body, dst: []Body, dt: f64 };

pub fn kick(s: Step, lo: usize, hi: usize) void {
    for (lo..hi) |i| {
        const b = s.src[i];
        var ax: f64 = 0.0;
        var ay: f64 = 0.0;
        var az: f64 = 0.0;
        for (s.src) |o| {
            const dx = o.x - b.x;
            const dy = o.y - b.y;
            const dz = o.z - b.z;
            const d2 = dx * dx + dy * dy + dz * dz + 0.01;
            const inv = o.m / (d2 * @sqrt(d2));
            ax += dx * inv;
            ay += dy * inv;
            az += dz * inv;
        }
        var nb = b;
        nb.vx = b.vx + ax * s.dt;
        nb.vy = b.vy + ay * s.dt;
        nb.vz = b.vz + az * s.dt;
        s.dst[i] = nb;
    }
}

pub fn drift(s: Step, lo: usize, hi: usize) void {
    for (lo..hi) |i| {
        var b = s.src[i];
        b.x = b.x + b.vx * s.dt;
        b.y = b.y + b.vy * s.dt;
        b.z = b.z + b.vz * s.dt;
        s.dst[i] = b;
    }
}

pub fn energy(bs: []const Body, lo: usize, hi: usize) f64 {
    var e: f64 = 0.0;
    for (lo..hi) |i| {
        const b = bs[i];
        const kin = 0.5 * b.m * (b.vx * b.vx + b.vy * b.vy + b.vz * b.vz);
        var pot: f64 = 0.0;
        for (bs, 0..) |o, j| {
            if (j != i) {
                const dx = o.x - b.x;
                const dy = o.y - b.y;
                const dz = o.z - b.z;
                pot += b.m * o.m / @sqrt(dx * dx + dy * dy + dz * dz + 0.01);
            }
        }
        e += kin - 0.5 * pot;
    }
    return e;
}

pub fn main(process: std.process.Init) !void {
    const args = try par.intArgs(process, 2, "nbody n steps");
    const n: usize = @intCast(args[0]);
    const workers = par.workerCount(process.environ_map);
    const a = try process.gpa.alloc(Body, n);
    defer process.gpa.free(a);
    const b = try process.gpa.alloc(Body, n);
    defer process.gpa.free(b);
    init(a);
    var k: i64 = 0;
    while (k < args[1]) : (k += 1) {
        par.forRange(workers, n, Step{ .src = a, .dst = b, .dt = 0.001 }, kick);
        par.forRange(workers, n, Step{ .src = b, .dst = a, .dt = 0.001 }, drift);
    }
    const e = par.sumRange(f64, workers, n, @as([]const Body, a), energy);
    try par.printLine(process.io, "{d:.17}", .{e});
}
