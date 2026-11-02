// React SSR on Bun: Bun.serve + react-dom/server renderToString.
import { render } from "./page";
const port = Number(process.argv[2] ?? 8080);
const server = Bun.serve({
  port,
  fetch(req) {
    const path = new URL(req.url).pathname;
    if (path === "/") return new Response("Hello, World!", { headers: { "Content-Type": "text/plain" } });
    if (path.startsWith("/page/")) {
      const n = Number(path.slice(6));
      if (!Number.isInteger(n) || n < 1 || n > 1000) return new Response("usage: /page/N, 1 <= N <= 1000", { status: 400 });
      return new Response(render(n), { headers: { "Content-Type": "text/html; charset=utf-8" } });
    }
    return new Response("Not Found", { status: 404, headers: { "Content-Type": "text/plain" } });
  },
});
console.error(`bun-react: serving on port ${server.port}`);
