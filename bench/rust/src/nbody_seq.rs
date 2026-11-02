// Sequential n-body for request handlers (the server is already parallel across connections).
#[derive(Clone, Copy)]
pub struct Body { pub x: f64, pub y: f64, pub z: f64, pub vx: f64, pub vy: f64, pub vz: f64, pub m: f64 }

pub fn init(n: usize) -> Vec<Body> {
    (0..n).map(|i| {
        let i = i as i64;
        Body { x: ((i * 2654435761) % 1009) as f64 / 1009.0, y: ((i * 40503) % 1013) as f64 / 1013.0,
               z: ((i * 69069) % 1019) as f64 / 1019.0, vx: 0.0, vy: 0.0, vz: 0.0, m: 1.0 / n as f64 }
    }).collect()
}
pub fn step(bs: &[Body], dt: f64) -> Vec<Body> {
    bs.iter().map(|b| {
        let (mut ax, mut ay, mut az) = (0.0f64, 0.0f64, 0.0f64);
        for o in bs {
            let dx = o.x - b.x; let dy = o.y - b.y; let dz = o.z - b.z;
            let d2 = dx * dx + dy * dy + dz * dz + 0.01;
            let inv = o.m / (d2 * d2.sqrt());
            ax += dx * inv; ay += dy * inv; az += dz * inv;
        }
        let (vx, vy, vz) = (b.vx + ax * dt, b.vy + ay * dt, b.vz + az * dt);
        Body { x: b.x + vx * dt, y: b.y + vy * dt, z: b.z + vz * dt, vx, vy, vz, m: b.m }
    }).collect()
}
pub fn energy(bs: &[Body]) -> f64 {
    bs.iter().enumerate().map(|(i, b)| {
        let kin = 0.5 * b.m * (b.vx * b.vx + b.vy * b.vy + b.vz * b.vz);
        let mut pot = 0.0;
        for (j, o) in bs.iter().enumerate() {
            if j != i {
                let dx = o.x - b.x; let dy = o.y - b.y; let dz = o.z - b.z;
                pot += b.m * o.m / (dx * dx + dy * dy + dz * dz + 0.01).sqrt();
            }
        }
        kin - 0.5 * pot
    }).sum()
}
pub fn simulate(n: usize, steps: usize) -> f64 {
    let mut bs = init(n);
    for _ in 0..steps { bs = step(&bs, 0.001); }
    energy(&bs)
}
