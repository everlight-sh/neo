import { renderToStaticMarkup } from "react-dom/server";
import { Page } from "./page";

export const nameFor = (count: number) => count === 13 ? '<script>alert("x")</script> & \' café 🚀' : 'Neo & React\'s "JSX" <components>';
export const render = (count: number) => "<!DOCTYPE html>" + renderToStaticMarkup(<Page name={nameFor(count)} count={count} featured={count % 2 === 0} />);

if (import.meta.main) {
  const port = Number(process.argv[2] || "8093");
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error("Port must be 1..65535");
  Bun.serve({ port, fetch(req) {
    if (req.method !== "GET") return new Response(null, { status: 405 });
    const url = new URL(req.url);
    if (url.pathname !== "/" && !url.pathname.startsWith("/page/")) return new Response("Not Found", { status: 404 });
    const digits = url.pathname.slice(6);
    const count = url.pathname === "/" ? 3 : /^\d{1,12}$/.test(digits) ? Number(digits) : 0;
    if (count < 1 || count > 1000) return new Response("usage: /page/N, 1 <= N <= 1000", { status: 400 });
    return new Response(render(count), { headers: { "Content-Type": "text/html; charset=utf-8" } });
  } });
  console.log(`React reference: http://localhost:${port}`);
}
