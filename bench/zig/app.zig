// Route logic shared by both Zig HTTP servers; the same routes and bodies as
// examples/http.neo and bench/rust/src/http_hyper.rs:
//   GET /            200 text/plain "Hello, World!"
//   GET /smooth/N    32 passes of a 3-point stencil over N values (1..1e6),
//                    {"n":N,"passes":32,"checksum":C}
//   POST /nbody      body {"n":1..4096,"steps":0..1000}; n-body energy,
//                    {"n":N,"steps":S,"energy":E} with 9 decimals
//   GET /page/N      catalog page (1..1000 rows), byte-identical to React's
//                    renderToString of bench/react/page.tsx
// Anything else: 404 for GET, 405 otherwise. Handlers allocate from a
// per-request arena supplied by the server.
const std = @import("std");

pub const passes = 32;

/// Decimal digits after `prefix` in `path`, within [lo, hi]; null otherwise.
pub fn parseBounded(text: []const u8, lo: u64, hi: u64) ?usize {
    const n = std.fmt.parseInt(u64, text, 10) catch return null;
    if (n < lo or n > hi) return null;
    return @intCast(n);
}

pub fn smoothChecksum(arena: std.mem.Allocator, n: usize) !i64 {
    var a = try arena.alloc(i64, n);
    var b = try arena.alloc(i64, n);
    for (a, 0..) |*x, i| x.* = @rem(@as(i64, @intCast(i)) * 2654435761, 1000003);
    for (0..passes) |_| {
        for (0..n) |i| {
            b[i] = if (i == 0 or i + 1 == n) a[i] else @rem(a[i - 1] + 2 * a[i] + a[i + 1], 1000003);
        }
        std.mem.swap([]i64, &a, &b);
    }
    var total: i64 = 0;
    for (a) |x| total += x;
    return total;
}

pub fn smoothBody(arena: std.mem.Allocator, n: usize) ![]u8 {
    return std.fmt.allocPrint(arena, "{{\"n\":{d},\"passes\":{d},\"checksum\":{d}}}", .{ n, passes, try smoothChecksum(arena, n) });
}

const Body = struct { x: f64, y: f64, z: f64, vx: f64, vy: f64, vz: f64, m: f64 };

/// Sequential n-body (the server is already concurrent across connections),
/// as bench/rust/src/nbody_seq.rs.
pub fn simulate(arena: std.mem.Allocator, n: usize, steps: usize) !f64 {
    var bs = try arena.alloc(Body, n);
    var next = try arena.alloc(Body, n);
    const fnum: f64 = @floatFromInt(n);
    for (bs, 0..) |*b, k| {
        const i: i64 = @intCast(k);
        b.* = .{
            .x = @as(f64, @floatFromInt(@rem(i * 2654435761, 1009))) / 1009.0,
            .y = @as(f64, @floatFromInt(@rem(i * 40503, 1013))) / 1013.0,
            .z = @as(f64, @floatFromInt(@rem(i * 69069, 1019))) / 1019.0,
            .vx = 0.0, .vy = 0.0, .vz = 0.0, .m = 1.0 / fnum,
        };
    }
    const dt = 0.001;
    for (0..steps) |_| {
        for (bs, next) |b, *out| {
            var ax: f64 = 0.0;
            var ay: f64 = 0.0;
            var az: f64 = 0.0;
            for (bs) |o| {
                const dx = o.x - b.x;
                const dy = o.y - b.y;
                const dz = o.z - b.z;
                const d2 = dx * dx + dy * dy + dz * dz + 0.01;
                const inv = o.m / (d2 * @sqrt(d2));
                ax += dx * inv;
                ay += dy * inv;
                az += dz * inv;
            }
            const vx = b.vx + ax * dt;
            const vy = b.vy + ay * dt;
            const vz = b.vz + az * dt;
            out.* = .{ .x = b.x + vx * dt, .y = b.y + vy * dt, .z = b.z + vz * dt, .vx = vx, .vy = vy, .vz = vz, .m = b.m };
        }
        std.mem.swap([]Body, &bs, &next);
    }
    var e: f64 = 0.0;
    for (bs, 0..) |b, i| {
        e += 0.5 * b.m * (b.vx * b.vx + b.vy * b.vy + b.vz * b.vz);
        var pot: f64 = 0.0;
        for (bs, 0..) |o, j| {
            if (j != i) {
                const dx = o.x - b.x;
                const dy = o.y - b.y;
                const dz = o.z - b.z;
                pot += b.m * o.m / @sqrt(dx * dx + dy * dy + dz * dz + 0.01);
            }
        }
        e -= 0.5 * pot;
    }
    return e;
}

pub const NbodyRequest = struct { n: i64, steps: i64 };

/// Response body for POST /nbody, or null when the request is invalid.
pub fn nbodyBody(arena: std.mem.Allocator, request_body: []const u8) !?[]u8 {
    const req = std.json.parseFromSliceLeaky(NbodyRequest, arena, request_body, .{ .ignore_unknown_fields = true }) catch return null;
    if (req.n < 1 or req.n > 4096 or req.steps < 0 or req.steps > 1000) return null;
    const e = try simulate(arena, @intCast(req.n), @intCast(req.steps));
    return try std.fmt.allocPrint(arena, "{{\"n\":{d},\"steps\":{d},\"energy\":{d:.9}}}", .{ req.n, req.steps, e });
}

pub const nbody_usage = "usage: POST /nbody {\"n\":1..4096,\"steps\":0..1000}";
pub const smooth_usage = "usage: /smooth/N, 1 <= N <= 1e6";
pub const page_usage = "usage: /page/N, 1 <= N <= 1000";

const words = [8][]const u8{ "Widget", "Gadget", "Gizmo", "Doohickey", "Sprocket", "Flange", "Bracket", "Grommet" };
const adjectives = [8][]const u8{ "Deluxe", "Basic", "Pro", "Mini", "Ultra", "Classic", "Eco", "Max" };

fn escapeInto(w: *std.Io.Writer, s: []const u8) !void {
    for (s) |c| switch (c) {
        '&' => try w.writeAll("&amp;"),
        '<' => try w.writeAll("&lt;"),
        '>' => try w.writeAll("&gt;"),
        '"' => try w.writeAll("&quot;"),
        '\'' => try w.writeAll("&#x27;"),
        else => try w.writeByte(c),
    };
}

pub fn page(w: *std.Io.Writer, n: usize) !void {
    try w.print("<!DOCTYPE html><html lang=\"en\"><head><title>Catalog</title></head><body><header><h1>Catalog</h1><p>{d} items", .{n});
    try w.writeAll("</p></header><main><table><thead><tr><th>ID</th><th>Name</th><th>Price</th><th>Stock</th><th>Note</th></tr></thead><tbody>");
    var cents: u64 = 0;
    for (0..n) |i| {
        const dollars = (i * 37) % 1000;
        const stock = (i * 13) % 50;
        cents += dollars * 100 + 99;
        try w.writeAll(if (i % 2 == 1) "<tr class=\"odd\"><td>" else "<tr class=\"even\"><td>");
        try w.print("{d}</td><td>{s} {s}</td><td>${d}.99</td><td>{d}</td><td>", .{ i, words[i % 8], adjectives[(i * 7) % 8], dollars, stock });
        if (i % 5 == 0) try escapeInto(w, "Ben & Jerry's \"Special\" <limited>") else try w.writeByte('-');
        try w.writeAll("</td></tr>");
    }
    try w.print("</tbody></table></main><footer>Total: ${d}.{d:0>2}</footer></body></html>", .{ cents / 100, cents % 100 });
}

pub fn pageBody(arena: std.mem.Allocator, n: usize) ![]u8 {
    var out: std.Io.Writer.Allocating = try .initCapacity(arena, 200 + n * 110);
    try page(&out.writer, n);
    return out.written();
}
