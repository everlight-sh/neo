// fetch() COUNT times: bun fetch.ts PORT PATH COUNT SIZE KEEP [CA.pem].
// KEEP 0 opens a connection per request, like fetch.neo; KEEP 1 reuses one.
// With a root certificate the requests use HTTPS. Prints the total
// nanoseconds and how many responses were 200 with SIZE bytes, then each
// request's nanoseconds.
const [port, path, count, size, keep, ca] = Bun.argv.slice(2);
const url = `${ca ? "https" : "http"}://127.0.0.1:${port}${path}`;
const options: RequestInit & { tls?: { ca: string } } = { keepalive: keep === "1" };
if (ca) options.tls = { ca: await Bun.file(ca).text() };
const times: number[] = [];
let good = 0;
const start = Bun.nanoseconds();
for (let i = 0; i < Number(count); i++) {
  const before = Bun.nanoseconds();
  const response = await fetch(url, options);
  const body = await response.arrayBuffer();
  times.push(Bun.nanoseconds() - before);
  if (response.status === 200 && body.byteLength === Number(size)) good++;
}
console.log(`${Bun.nanoseconds() - start} ${good}\n${times.join(" ")}`);
