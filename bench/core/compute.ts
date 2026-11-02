// Standalone Bun counterparts of the existing native compute workloads.
const [kind, ...args] = process.argv.slice(2);
const n = Number(args[0]);
if (kind === "mandel") {
  const h = Number(args[1]), maximum = Number(args[2]);
  let total = 0;
  for (let y = 0; y < h; y++) {
    const cy = -1.5 + 3 * y / h;
    for (let x = 0; x < n; x++) {
      const cx = -2 + 3 * x / n;
      let zx = 0, zy = 0, k = 0;
      while (k < maximum && zx*zx + zy*zy <= 4) {
        const next = zx*zx - zy*zy + cx;
        zy = 2*zx*zy + cy; zx = next; k++;
      }
      total += k;
    }
  }
  console.log(total);
} else if (kind === "stencil") {
  let a = new Float64Array(n), b = new Float64Array(n);
  for (let i = 0; i < n; i++) a[i] = (i * 2654435761) % 1000003;
  for (let pass = 0; pass < Number(args[1]); pass++) {
    for (let i = 0; i < n; i++) b[i] = i === 0 || i + 1 === n ? a[i] : (a[i-1] + 2*a[i] + a[i+1]) % 1000003;
    [a, b] = [b, a];
  }
  let sum = 0; for (const value of a) sum += value;
  console.log(sum);
} else if (kind === "nbody") {
  // Same array-of-objects equations as bench/bun/server.ts; dt=0.001.
  type Body = { x:number; y:number; z:number; vx:number; vy:number; vz:number; m:number };
  let bodies: Body[] = Array.from({length:n}, (_, i) => ({x:((i*2654435761)%1009)/1009, y:((i*40503)%1013)/1013, z:((i*69069)%1019)/1019, vx:0, vy:0, vz:0, m:1/n}));
  for (let step = 0; step < Number(args[1]); step++) {
    const next = new Array<Body>(n);
    for (let i = 0; i < n; i++) {
      const b = bodies[i]; let ax=0, ay=0, az=0;
      for (let j = 0; j < n; j++) {
        const other=bodies[j], dx=other.x-b.x, dy=other.y-b.y, dz=other.z-b.z;
        const d2=dx*dx+dy*dy+dz*dz+0.01, inv=other.m/(d2*Math.sqrt(d2));
        ax+=dx*inv; ay+=dy*inv; az+=dz*inv;
      }
      const vx=b.vx+ax*0.001, vy=b.vy+ay*0.001, vz=b.vz+az*0.001;
      next[i]={x:b.x+vx*0.001,y:b.y+vy*0.001,z:b.z+vz*0.001,vx,vy,vz,m:b.m};
    }
    bodies=next;
  }
  let energy=0;
  for (let i=0;i<n;i++) {
    const b=bodies[i]; energy+=0.5*b.m*(b.vx*b.vx+b.vy*b.vy+b.vz*b.vz);
    let potential=0;
    for (let j=0;j<n;j++) if (j!==i) {
      const other=bodies[j], dx=other.x-b.x, dy=other.y-b.y, dz=other.z-b.z;
      potential+=b.m*other.m/Math.sqrt(dx*dx+dy*dy+dz*dz+0.01);
    }
    energy-=0.5*potential;
  }
  console.log(energy);
} else throw Error("mandel|stencil|nbody expected");
