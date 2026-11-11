// Generate both renderers from the same TSX; neither variant caches responses.
import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { compile } from "./compile";

const here = import.meta.dir, root = resolve(here, "../..");
const out = resolve(root, ".kernel-build/jsx-ssr");
const source = await readFile(resolve(here, "page.tsx"), "utf8");
const baseline = compile(source, "page.tsx", { optimize: false }).replace(/\bjsx_(Badge|Card|Page)\b/g, "jsx_Baseline$1");
const optimized = compile(source, "page.tsx");
const app = `
fn bench_name (n : i64) -> Arr u8 _
  = if n == 13 then "<script>alert(\\\"x\\\")</script> & \\' café 🚀"
    else "Neo & React\\'s \\\"JSX\\\" <components>"

fn bench_checksum (body : Arr u8 n) -> i64
  = sum(i in 0..n) i64(body[i])

fn bench_render (n : i64{n >= 0}, mode : i64) -> i64
  = let body = concat("<!DOCTYPE html>",
      if mode == 0 then jsx_BaselinePage(bench_name(n), n, n % 2 == 0)
      else jsx_Page(bench_name(n), n, n % 2 == 0)) in
    bench_checksum(body)

effect fn main (iterations : i64{iterations > 0}, mode : i64) -> i64
  = loop (i : i64{i >= 0} = 0, checksum = 0)
      while i < iterations
      next (i + 1, checksum + bench_render(i % 1000 + 1, mode))
      yield checksum
`;
const path = resolve(out, "render-bench.neo"), binary = resolve(out, "render-bench");
await writeFile(path, [await readFile(resolve(here, "html.neo"), "utf8"), baseline, optimized, app].join("\n"));
const child = Bun.spawn([resolve(root, "neo"), "build", path, "-o", binary], { cwd: root, stdout: "inherit", stderr: "inherit" });
process.exit(await child.exited);
