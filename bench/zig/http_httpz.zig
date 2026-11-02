// HTTP server on karlseguin/http.zig (httpz): epoll workers parse requests
// and hand them to a thread pool that runs the handlers. Routes and bodies:
// see app.zig. Usage: http_httpz PORT
// HTTPZ_WORKERS / HTTPZ_POOL override workers.count / thread_pool.count
// (library defaults: 1 and 32).
const std = @import("std");
const httpz = @import("httpz");
const app = @import("app.zig");

fn envCount(env: *const std.process.Environ.Map, name: []const u8, default: u16) u16 {
    const value = env.get(name) orelse return default;
    return std.fmt.parseInt(u16, value, 10) catch default;
}

pub fn main(init: std.process.Init) !void {
    const args = try init.minimal.args.toSlice(init.arena.allocator());
    if (args.len != 2) {
        std.debug.print("usage: http_httpz PORT\n", .{});
        std.process.exit(2);
    }
    const port = try std.fmt.parseInt(u16, args[1], 10);
    var server = try httpz.Server(void).init(init.io, init.gpa, .{
        .address = .all(port),
        .workers = .{ .count = envCount(init.environ_map, "HTTPZ_WORKERS", 1) },
        .thread_pool = .{ .count = envCount(init.environ_map, "HTTPZ_POOL", 32) },
    }, {});
    defer server.deinit();
    var router = try server.router(.{});
    router.get("/", hello, .{});
    router.get("/smooth/:n", smooth, .{});
    router.get("/page/:n", page, .{});
    router.post("/nbody", nbody, .{});
    try server.listen();
}

fn hello(_: *httpz.Request, res: *httpz.Response) !void {
    res.content_type = .TEXT;
    res.body = "Hello, World!";
}

fn smooth(req: *httpz.Request, res: *httpz.Response) !void {
    if (app.parseBounded(req.param("n").?, 1, 1_000_000)) |n| {
        res.content_type = .JSON;
        res.body = try app.smoothBody(res.arena, n);
    } else {
        res.status = 400;
        res.content_type = .TEXT;
        res.body = app.smooth_usage;
    }
}

fn page(req: *httpz.Request, res: *httpz.Response) !void {
    if (app.parseBounded(req.param("n").?, 1, 1000)) |n| {
        res.content_type = .HTML;
        try app.page(res.writer(), n);
    } else {
        res.status = 400;
        res.content_type = .TEXT;
        res.body = app.page_usage;
    }
}

fn nbody(req: *httpz.Request, res: *httpz.Response) !void {
    if (try app.nbodyBody(res.arena, req.body() orelse "")) |out| {
        res.content_type = .JSON;
        res.body = out;
    } else {
        res.status = 400;
        res.content_type = .TEXT;
        res.body = app.nbody_usage;
    }
}
