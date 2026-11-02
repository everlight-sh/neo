const workers = Number(process.env.BENCH_WORKERS || "1");
const port = Number(process.argv[2] || "8080");
if (workers > 1 && !process.env.BENCH_CHILD) {
  const children = Array.from({ length: workers }, () => Bun.spawn([process.execPath, import.meta.path, String(port)], {
    env: { ...process.env, BENCH_WORKERS: "1", BENCH_CHILD: "1" }, stdout: "inherit", stderr: "inherit",
  }));
  const stop = () => { for (const child of children) child.kill(); process.exit(0); };
  process.on("SIGTERM", stop); process.on("SIGINT", stop);
  // A failed rendering child makes the container fail instead of hiding it.
  const status = await Promise.race(children.map(c => c.exited));
  for (const child of children) child.kill();
  process.exit(status || 1);
} else {
  const { render } = process.env.RENDERER === "react" ? await import("./reference.tsx") : await import("./direct.ts");
  Bun.serve({ port, reusePort: process.env.BENCH_CHILD === "1", fetch(req) {
    if (req.method !== "GET") return new Response(null, { status: 405 });
    const path = new URL(req.url).pathname;
    if (path !== "/" && !path.startsWith("/page/")) return new Response("Not Found", { status: 404 });
    const digits = path.slice(6);
    const count = path === "/" ? 3 : /^\d{1,12}$/.test(digits) ? Number(digits) : 0;
    if (count < 1 || count > 1000) return new Response("usage: /page/N, 1 <= N <= 1000", { status: 400 });
    return new Response(render(count), { headers: { "Content-Type": "text/html; charset=utf-8" } });
  } });
  console.log(`bun ${process.env.RENDERER}: ready, pid=${process.pid}`);
}
