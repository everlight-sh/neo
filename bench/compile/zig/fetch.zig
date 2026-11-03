// GET with std.http.Client COUNT times: fetch PORT PATH COUNT SIZE KEEP [CA.pem],
// the interface of bench/fetch's Go and Rust clients (zig 0.17.0). KEEP 0 opens
// a connection per request; KEEP 1 reuses one. With a root certificate the
// requests use HTTPS, verified against that root only. Prints the total
// nanoseconds and how many responses were 200 with SIZE bytes, then each
// request's nanoseconds. Built by bench/compile/run.py for compile times.
const std = @import("std");
const Io = std.Io;

pub fn main(init: std.process.Init) !void {
    const io = init.io;
    const gpa = init.gpa;
    const arena = init.arena.allocator();
    const args = try init.minimal.args.toSlice(arena);
    if (args.len < 6) {
        std.debug.print("usage: fetch PORT PATH COUNT SIZE KEEP [CA.pem]\n", .{});
        std.process.exit(2);
    }
    const count = try std.fmt.parseInt(usize, args[3], 10);
    const size = try std.fmt.parseInt(usize, args[4], 10);
    const keep = std.mem.eql(u8, args[5], "1");

    var client: std.http.Client = .{ .allocator = gpa, .io = io };
    defer client.deinit();
    var scheme: []const u8 = "http";
    if (args.len > 6) {
        const now = Io.Clock.real.now(io);
        try client.ca_bundle.addCertsFromFilePath(gpa, io, now, Io.Dir.cwd(), args[6]);
        client.now = now; // the bundle is loaded: no system rescan
        scheme = "https";
    }
    const url = try std.fmt.allocPrint(arena, "{s}://127.0.0.1:{s}{s}", .{ scheme, args[1], args[2] });

    var body: Io.Writer.Allocating = .init(gpa);
    defer body.deinit();
    const times = try arena.alloc(i96, count);
    var good: usize = 0;
    const start = Io.Clock.awake.now(io);
    for (times) |*t| {
        const before = Io.Clock.awake.now(io);
        body.clearRetainingCapacity();
        const result = try client.fetch(.{ .location = .{ .url = url }, .response_writer = &body.writer, .keep_alive = keep });
        if (result.status == .ok and body.written().len == size) good += 1;
        t.* = before.untilNow(io, .awake).toNanoseconds();
    }
    const total = start.untilNow(io, .awake).toNanoseconds();

    var buf: [4096]u8 = undefined;
    var w = Io.File.stdout().writerStreaming(io, &buf);
    try w.interface.print("{d} {d}\n", .{ total, good });
    for (times) |t| try w.interface.print("{d}\n", .{t});
    try w.interface.flush();
}
