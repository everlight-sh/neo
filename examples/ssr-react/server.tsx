import { render } from "./page";

const port = Number(process.argv[2] ?? 8091);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error("usage: bun run server.tsx PORT (1..65535)");
}

const server = Bun.serve({
  port,
  fetch(request) {
    if (request.method !== "GET") return new Response(null, { status: 405 });
    const path = new URL(request.url).pathname;
    let count: number;
    if (path === "/") count = 3;
    else if (path.startsWith("/page/")) {
      const digits = path.slice(6);
      count = /^\d{1,12}$/.test(digits) ? Number(digits) : -1;
      if (count < 1 || count > 1000) {
        return new Response("usage: /page/N, 1 <= N <= 1000", { status: 400 });
      }
    } else return new Response("Not Found", { status: 404 });

    // Render for every request: no response cache or pre-rendered document.
    return new Response(render(count), {
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });
  },
});
console.error(`bun-react: http://localhost:${server.port} (${process.env.NODE_ENV ?? "development"})`);
