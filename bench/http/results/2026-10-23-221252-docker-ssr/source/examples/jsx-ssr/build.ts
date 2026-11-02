import { mkdir, readFile, rename, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { compile } from "./compile";

const here = import.meta.dir;
const root = resolve(here, "../..");
const out = resolve(here, "../../.kernel-build/jsx-ssr");
await mkdir(out, { recursive: true });
const componentSource = await readFile(resolve(here, "page.tsx"), "utf8");
const generated = compile(componentSource, "page.tsx", { optimize: process.env.AXON_JSX_OPT !== "0" });
// The demo's Axon route calls this exact entry point. Other components may vary.
if (!generated.includes("fn jsx_Page (p_name : Arr u8 n0, p_count : i64{p_count >= 0}, p_featured : bool)")) {
  throw new Error("The demo route requires Page({ name: string, count: number, featured: boolean }) in that order");
}
const source = [await readFile(resolve(here, "html.ax"), "utf8"), generated,
  await readFile(resolve(here, "server.ax"), "utf8")].join("\n");
await writeFile(resolve(out, "components.ax"), generated);
await writeFile(resolve(out, "server.ax"), source);
const binary = process.argv[2] ? resolve(process.argv[2]) : resolve(out, "server");
// Publish a new inode atomically, so rebuilding a running macOS demo does not
// invalidate its mapped code or reuse stale executable signature cache entries.
const staging = `${binary}.building-${process.pid}`;
const child = Bun.spawn(["python3", "-m", "axonc", "build", resolve(out, "server.ax"), "-o", staging], {
  cwd: root, stdout: "inherit", stderr: "inherit",
});
const status = await child.exited;
if (status) { await rm(staging, { force: true }); process.exit(status); }
await rename(staging, binary);
console.log(`Generated Axon: ${out}/components.ax\nRun: AXON_THREADS=1 ${binary} 8092`);
