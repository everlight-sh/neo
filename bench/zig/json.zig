// std.json on the same inputs as bench/rust/src/typed_json.rs:
//   doc-value N | doc-typed N    small document built and decoded N times
//                                (examples/library_bench.neo, mode 0)
//   orders-value N | orders-typed N  1,000-order array built once, decoded
//                                N times (bench/core/orders_json.neo 1000 N)
// "value" parses into std.json.Value (dynamic, like serde_json::Value);
// "typed" parses into structs (like serde derive). By default every parse
// goes through std.json.parseFromSlice and is freed with deinit before the
// next one. Appending "-arena" to a mode instead reuses one ArenaAllocator
// (reset with retain_capacity) and parseFromSliceLeaky: the usual Zig tuning
// for repeated parses.
const std = @import("std");
const par = @import("par.zig");

const Document = struct { id: i64, name: []const u8, active: bool, values: []const i64 };
const Order = struct { customer: i64, qty: i64, price: i64, name: []const u8 };

fn docValue(v: std.json.Value) i64 {
    const o = v.object;
    return o.get("id").?.integer + @as(i64, @intCast(o.get("name").?.string.len + o.get("values").?.array.items.len)) + 1;
}

fn docTyped(d: Document) i64 {
    return d.id + @as(i64, @intCast(d.name.len + d.values.len)) + 1;
}

fn ordersValue(v: std.json.Value) i64 {
    var sum: i64 = 0;
    for (v.array.items) |row| {
        const r = row.object;
        sum += r.get("qty").?.integer * r.get("price").?.integer + r.get("customer").?.integer +
            @as(i64, @intCast(r.get("name").?.string.len));
    }
    return sum;
}

fn ordersTyped(rows: []const Order) i64 {
    var sum: i64 = 0;
    for (rows) |r| sum += r.qty * r.price + r.customer + @as(i64, @intCast(r.name.len));
    return sum;
}

fn decode(comptime T: type, comptime fold: fn (T) i64, gpa: std.mem.Allocator, arena: ?*std.heap.ArenaAllocator, source: []const u8) !i64 {
    if (arena) |a| {
        _ = a.reset(.retain_capacity);
        return fold(try std.json.parseFromSliceLeaky(T, a.allocator(), source, .{}));
    }
    const parsed = try std.json.parseFromSlice(T, gpa, source, .{});
    defer parsed.deinit();
    return fold(parsed.value);
}

fn ordersText(gpa: std.mem.Allocator, n: usize) ![]u8 {
    var out: std.Io.Writer.Allocating = .init(gpa);
    errdefer out.deinit();
    try out.writer.writeByte('[');
    for (0..n) |i| {
        if (i != 0) try out.writer.writeByte(',');
        try out.writer.print("{{\"customer\":{d},\"qty\":{d},\"price\":3,\"name\":\"user{d}\"}}", .{ i % 8, i % 17, i });
    }
    try out.writer.writeByte(']');
    return out.toOwnedSlice();
}

pub fn main(init: std.process.Init) !void {
    const gpa = init.gpa;
    const args = try init.minimal.args.toSlice(init.arena.allocator());
    if (args.len != 3) {
        std.debug.print("usage: json doc-value|doc-typed|orders-value|orders-typed[-arena] N\n", .{});
        std.process.exit(2);
    }
    const mode = args[1];
    const n = try std.fmt.parseInt(i64, args[2], 10);
    var arena_state = std.heap.ArenaAllocator.init(gpa);
    defer arena_state.deinit();
    const arena: ?*std.heap.ArenaAllocator = if (std.mem.endsWith(u8, mode, "-arena")) &arena_state else null;
    const typed = std.mem.indexOf(u8, mode, "-typed") != null;
    var sum: i64 = 0;
    if (std.mem.startsWith(u8, mode, "doc-")) {
        var buf: [128]u8 = undefined;
        var i: i64 = 0;
        while (i < n) : (i += 1) {
            const source = try std.fmt.bufPrint(&buf, "{{\"id\":{d},\"name\":\"café 🚀\",\"active\":true,\"values\":[1,2,3]}}", .{@rem(i, 1000)});
            sum += if (typed)
                try decode(Document, docTyped, gpa, arena, source)
            else
                try decode(std.json.Value, docValue, gpa, arena, source);
        }
    } else if (std.mem.startsWith(u8, mode, "orders-")) {
        const text = try ordersText(gpa, 1000);
        defer gpa.free(text);
        var k: i64 = 0;
        while (k < n) : (k += 1) {
            sum += if (typed)
                try decode([]const Order, ordersTyped, gpa, arena, text)
            else
                try decode(std.json.Value, ordersValue, gpa, arena, text);
        }
    } else return error.UnknownMode;
    try par.printLine(init.io, "{d}", .{sum});
}
