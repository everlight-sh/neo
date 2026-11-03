const std = @import("std");

pub fn main(init: std.process.Init) !void {
    var buf: [64]u8 = undefined;
    var w = std.Io.File.stdout().writerStreaming(init.io, &buf);
    try w.interface.writeAll("Hello, World!\n");
    try w.interface.flush();
}
