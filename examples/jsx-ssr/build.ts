import { mkdir, readFile, rename, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { compile } from "./compile";

const here = import.meta.dir;
const root = resolve(here, "../..");
const out = resolve(here, "../../.kernel-build/jsx-ssr");
await mkdir(out, { recursive: true });
const componentSource = await readFile(resolve(here, "page.tsx"), "utf8");
const generated = compile(componentSource, "page.tsx", { optimize: process.env.NEO_JSX_OPT !== "0" });
// The demo's Neo route calls this exact entry point. Other components may vary.
if (!generated.includes("fn jsx_Page (p_name : Arr u8 n0, p_count : i64{p_count >= 0}, p_featured : bool)")) {
  throw new Error("The demo route requires Page({ name: string, count: number, featured: boolean }) in that order");
}
const source = [await readFile(resolve(here, "html.neo"), "utf8"), generated,
  await readFile(resolve(here, "server.neo"), "utf8")].join("\n");
await writeFile(resolve(out, "components.neo"), generated);
await writeFile(resolve(out, "server.neo"), source);
const binary = process.argv[2] ? resolve(process.argv[2]) : resolve(out, "server");
// Publish a new inode atomically, so rebuilding a running macOS demo does not
// invalidate its mapped code or reuse stale executable signature cache entries.
const staging = `${binary}.building-${process.pid}`;
const child = Bun.spawn([resolve(root, "neo"), "build", resolve(out, "server.neo"), "-o", staging], {
  cwd: root, stdout: "inherit", stderr: "inherit",
});
const status = await child.exited;
if (status) { await rm(staging, { force: true }); process.exit(status); }
await rename(staging, binary);
console.log(`Generated Neo: ${out}/components.neo\nRun: NEO_THREADS=1 ${binary} 8092`);
