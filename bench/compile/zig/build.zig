// One step per compile-time benchmark program (zig 0.17.0): zig build NAME
// -Doptimize=ReleaseFast. The report timed `zig build-exe`, which never caches
// its output, so its unchanged rebuild compiles everything again; this file
// measures the unchanged rebuild through the build system's cache instead.
const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});
    const programs = [_][2][]const u8{
        .{ "hello", "hello.zig" },
        .{ "fetch", "fetch.zig" },
        .{ "http", "../../zig/http_std.zig" },
        .{ "json", "../../zig/json.zig" },
        .{ "nbody", "../../zig/nbody.zig" },
    };
    for (programs) |program| {
        const exe = b.addExecutable(.{ .name = program[0], .root_module = b.createModule(.{
            .root_source_file = b.path(program[1]),
            .target = target,
            .optimize = optimize,
        }) });
        b.step(program[0], b.fmt("build {s}", .{program[0]})).dependOn(&b.addInstallArtifact(exe, .{}).step);
    }
}
