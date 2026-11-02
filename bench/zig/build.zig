// zig build -Doptimize=ReleaseFast -Dcpu=baseline   (zig 0.17.0)
// Builds the compute ports, the JSON workload and both HTTP servers into
// zig-out/bin. -Dcpu=baseline matches the generic x86-64 code Vif (clang
// without -march) and the earlier Rust builds emit; omit it for -mcpu=native.
const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const plain = [_][]const u8{ "mandel", "stencil", "nbody", "sieve", "json", "http_std" };
    for (plain) |name| {
        const exe = b.addExecutable(.{
            .name = name,
            .root_module = b.createModule(.{
                .root_source_file = b.path(b.fmt("{s}.zig", .{name})),
                .target = target,
                .optimize = optimize,
            }),
        });
        b.installArtifact(exe);
    }

    const httpz = b.dependency("httpz", .{ .target = target, .optimize = optimize });
    const exe = b.addExecutable(.{
        .name = "http_httpz",
        .root_module = b.createModule(.{
            .root_source_file = b.path("http_httpz.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{.{ .name = "httpz", .module = httpz.module("httpz") }},
        }),
    });
    b.installArtifact(exe);
}
