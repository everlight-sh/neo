// HTTP server on the standard library only: std.Io.net for sockets,
// std.http.Server for HTTP/1.1 framing, one std.Io `concurrent` task per
// connection (with the default threaded Io, a thread per connection).
// Routes and bodies: see app.zig. Usage: http_std PORT
const std = @import("std");
const Io = std.Io;
const app = @import("app.zig");

pub fn main(init: std.process.Init) !void {
    const io = init.io;
    const args = try init.minimal.args.toSlice(init.arena.allocator());
    if (args.len != 2) {
        std.debug.print("usage: http_std PORT\n", .{});
        std.process.exit(2);
    }
    const port = try std.fmt.parseInt(u16, args[1], 10);
    const address = try Io.net.IpAddress.parse("0.0.0.0", port);
    var listener = try address.listen(io, .{ .reuse_address = true });
    defer listener.deinit(io);
    var group: Io.Group = .init;
    defer group.cancel(io);
    while (true) {
        const stream = listener.accept(io) catch |err| switch (err) {
            error.ConnectionAborted => continue,
            else => return err,
        };
        group.concurrent(io, serveConnection, .{ io, init.gpa, stream }) catch stream.close(io);
    }
}

fn serveConnection(io: Io, gpa: std.mem.Allocator, stream: Io.net.Stream) void {
    defer stream.close(io);
    const one: c_int = 1;
    std.posix.setsockopt(stream.socket.handle, std.posix.IPPROTO.TCP, std.posix.TCP.NODELAY, std.mem.asBytes(&one)) catch {};
    var recv_buffer: [8192]u8 = undefined;
    var send_buffer: [8192]u8 = undefined;
    var reader = stream.reader(io, &recv_buffer);
    var writer = stream.writer(io, &send_buffer);
    var server = std.http.Server.init(&reader.interface, &writer.interface);
    var arena = std.heap.ArenaAllocator.init(gpa);
    defer arena.deinit();
    while (true) {
        var request = server.receiveHead() catch return;
        handle(&request, arena.allocator()) catch return;
        _ = arena.reset(.retain_capacity);
    }
}

const text = [_]std.http.Header{.{ .name = "content-type", .value = "text/plain" }};
const json = [_]std.http.Header{.{ .name = "content-type", .value = "application/json" }};
const html = [_]std.http.Header{.{ .name = "content-type", .value = "text/html; charset=utf-8" }};

fn handle(request: *std.http.Server.Request, arena: std.mem.Allocator) !void {
    const method = request.head.method;
    const target = request.head.target;
    if (method == .POST and std.mem.eql(u8, target, "/nbody")) {
        const length = request.head.content_length orelse 0;
        if (length > 4096) return request.respond(app.nbody_usage, .{ .status = .bad_request, .extra_headers = &text });
        const body = try arena.alloc(u8, @intCast(length));
        var body_buffer: [512]u8 = undefined;
        const body_reader = try request.readerExpectContinue(&body_buffer);
        try body_reader.readSliceAll(body);
        return if (try app.nbodyBody(arena, body)) |out|
            request.respond(out, .{ .extra_headers = &json })
        else
            request.respond(app.nbody_usage, .{ .status = .bad_request, .extra_headers = &text });
    }
    if (method != .GET) return request.respond("", .{ .status = .method_not_allowed });
    if (std.mem.eql(u8, target, "/")) return request.respond("Hello, World!", .{ .extra_headers = &text });
    if (std.mem.startsWith(u8, target, "/smooth/")) {
        return if (app.parseBounded(target["/smooth/".len..], 1, 1_000_000)) |n|
            request.respond(try app.smoothBody(arena, n), .{ .extra_headers = &json })
        else
            request.respond(app.smooth_usage, .{ .status = .bad_request, .extra_headers = &text });
    }
    if (std.mem.startsWith(u8, target, "/page/")) {
        return if (app.parseBounded(target["/page/".len..], 1, 1000)) |n|
            request.respond(try app.pageBody(arena, n), .{ .extra_headers = &html })
        else
            request.respond(app.page_usage, .{ .status = .bad_request, .extra_headers = &text });
    }
    return request.respond("Not Found", .{ .status = .not_found, .extra_headers = &text });
}
