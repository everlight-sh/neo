// Idiomatic Bun: Bun.serve (uWebSockets-based HTTP core, handler in JavaScript).
// GET /smooth/N runs 32 passes of a 3-point stencil over an N-element signal and returns JSON.
// BUN_REUSE_PORT=1 lets several processes share the port (Linux load-balances; macOS does not).
const port = Number(process.argv[2] ?? 8080);
const PASSES = 32;

function stencil(xs: Float64Array, out: Float64Array) {
  const n = xs.length;
  for (let i = 0; i < n; i++) {
    out[i] = i === 0 || i + 1 === n ? xs[i] : (xs[i - 1] + 2 * xs[i] + xs[i + 1]) % 1000003;
  }
}

function checksum(n: number): number {
  let a = new Float64Array(n);
  let b = new Float64Array(n);
  for (let i = 0; i < n; i++) a[i] = (i * 2654435761) % 1000003;   // exact: < 2^53
  for (let k = 0; k < PASSES; k++) {
    stencil(a, b);
    [a, b] = [b, a];
  }
  let s = 0;
  for (let i = 0; i < n; i++) s += a[i];
  return s;
}

// ---- n-body for POST /nbody (idiomatic JS: array of objects)
type B = { x: number; y: number; z: number; vx: number; vy: number; vz: number; m: number };
function nbodyInit(n: number): B[] {
  const bs: B[] = [];
  for (let i = 0; i < n; i++) {
    bs.push({ x: ((i * 2654435761) % 1009) / 1009.0, y: ((i * 40503) % 1013) / 1013.0, z: ((i * 69069) % 1019) / 1019.0,
              vx: 0, vy: 0, vz: 0, m: 1.0 / n });
  }
  return bs;
}
function nbodyStep(bs: B[], dt: number): B[] {
  const out: B[] = new Array(bs.length);
  for (let i = 0; i < bs.length; i++) {
    const b = bs[i];
    let ax = 0, ay = 0, az = 0;
    for (let j = 0; j < bs.length; j++) {
      const o = bs[j];
      const dx = o.x - b.x, dy = o.y - b.y, dz = o.z - b.z;
      const d2 = dx * dx + dy * dy + dz * dz + 0.01;
      const inv = o.m / (d2 * Math.sqrt(d2));
      ax += dx * inv; ay += dy * inv; az += dz * inv;
    }
    const vx = b.vx + ax * dt, vy = b.vy + ay * dt, vz = b.vz + az * dt;
    out[i] = { x: b.x + vx * dt, y: b.y + vy * dt, z: b.z + vz * dt, vx, vy, vz, m: b.m };
  }
  return out;
}
function nbodyEnergy(bs: B[]): number {
  let e = 0;
  for (let i = 0; i < bs.length; i++) {
    const b = bs[i];
    e += 0.5 * b.m * (b.vx * b.vx + b.vy * b.vy + b.vz * b.vz);
    let pot = 0;
    for (let j = 0; j < bs.length; j++) {
      if (j !== i) {
        const o = bs[j];
        const dx = o.x - b.x, dy = o.y - b.y, dz = o.z - b.z;
        pot += b.m * o.m / Math.sqrt(dx * dx + dy * dy + dz * dz + 0.01);
      }
    }
    e -= 0.5 * pot;
  }
  return e;
}
function simulate(n: number, steps: number): number {
  let bs = nbodyInit(n);
  for (let k = 0; k < steps; k++) bs = nbodyStep(bs, 0.001);
  return nbodyEnergy(bs);
}

const server = Bun.serve({
  port,
  reusePort: !!process.env.BUN_REUSE_PORT,
  async fetch(req) {
    const path = new URL(req.url).pathname;
    if (req.method === "POST" && path === "/nbody") {
      let body: any;
      try { body = await req.json(); } catch { body = null; }
      const n = body?.n, steps = body?.steps;
      if (!Number.isInteger(n) || !Number.isInteger(steps) || n < 1 || n > 4096 || steps < 0 || steps > 1000) {
        return new Response('usage: POST /nbody {"n":1..4096,"steps":0..1000}', { status: 400, headers: { "Content-Type": "text/plain" } });
      }
      return new Response(`{"n":${n},"steps":${steps},"energy":${simulate(n, steps).toFixed(9)}}`, { headers: { "Content-Type": "application/json" } });
    }
    if (path === "/") {
      return new Response("Hello, World!", { headers: { "Content-Type": "text/plain" } });
    }
    if (path.startsWith("/smooth/")) {
      const n = Number(path.slice(8));
      if (!Number.isInteger(n) || n < 1 || n > 1_000_000) {
        return new Response("usage: /smooth/N, 1 <= N <= 1e6", { status: 400, headers: { "Content-Type": "text/plain" } });
      }
      return new Response(JSON.stringify({ n, passes: PASSES, checksum: checksum(n) }), {
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response("Not Found", { status: 404, headers: { "Content-Type": "text/plain" } });
  },
});
console.error(`bun: serving on port ${server.port} (pid ${process.pid})`);
