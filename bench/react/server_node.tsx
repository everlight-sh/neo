// React SSR on Node: node:http + react-dom/server renderToString.
// NODE_CLUSTER=<workers> forks that many processes sharing the port (node:cluster).
import http from "node:http";
import cluster from "node:cluster";
import os from "node:os";
import { render } from "./page";

const port = Number(process.argv[2] ?? 8080);
const workers = Number(process.env.NODE_CLUSTER ?? 0);

function serve() {
  http.createServer((req, res) => {
    const path = (req.url ?? "/").split("?")[0];
    if (path === "/") { res.writeHead(200, { "Content-Type": "text/plain" }); res.end("Hello, World!"); return; }
    if (path.startsWith("/page/")) {
      const n = Number(path.slice(6));
      if (!Number.isInteger(n) || n < 1 || n > 1000) { res.writeHead(400); res.end("usage: /page/N, 1 <= N <= 1000"); return; }
      const html = render(n);
      res.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Content-Length": Buffer.byteLength(html) });
      res.end(html);
      return;
    }
    res.writeHead(404, { "Content-Type": "text/plain" }); res.end("Not Found");
  }).listen(port, () => console.error(`node-react: serving on port ${port} (pid ${process.pid})`));
}

if (workers > 0 && cluster.isPrimary) {
  for (let i = 0; i < Math.min(workers, os.cpus().length); i++) cluster.fork();
} else {
  serve();
}
