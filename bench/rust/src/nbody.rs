// Idiomatic Rust n-body: a Vec of Body structs (array-of-structs), rayon over
// bodies for the force computation, plain loops inside. Same model and
// initial conditions as examples/nbody.neo; softening 0.01, dt 0.001.
use rayon::prelude::*;

#[derive(Clone, Copy)]
struct Body { x: f64, y: f64, z: f64, vx: f64, vy: f64, vz: f64, m: f64 }

fn init(n: usize) -> Vec<Body> {
    (0..n).map(|i| {
        let i = i as i64;
        Body {
            x: ((i * 2654435761) % 1009) as f64 / 1009.0,
            y: ((i * 40503) % 1013) as f64 / 1013.0,
            z: ((i * 69069) % 1019) as f64 / 1019.0,
            vx: 0.0, vy: 0.0, vz: 0.0, m: 1.0 / n as f64,
        }
    }).collect()
}

fn kick(bs: &[Body], dt: f64) -> Vec<Body> {
    bs.par_iter().map(|b| {
        let (mut ax, mut ay, mut az) = (0.0f64, 0.0f64, 0.0f64);
        for o in bs {
            let dx = o.x - b.x; let dy = o.y - b.y; let dz = o.z - b.z;
            let d2 = dx * dx + dy * dy + dz * dz + 0.01;
            let inv = o.m / (d2 * d2.sqrt());
            ax += dx * inv; ay += dy * inv; az += dz * inv;
        }
        Body { vx: b.vx + ax * dt, vy: b.vy + ay * dt, vz: b.vz + az * dt, ..*b }
    }).collect()
}

fn drift(bs: &[Body], dt: f64) -> Vec<Body> {
    bs.par_iter().map(|b| Body { x: b.x + b.vx * dt, y: b.y + b.vy * dt, z: b.z + b.vz * dt, ..*b }).collect()
}

fn energy(bs: &[Body]) -> f64 {
    bs.par_iter().enumerate().map(|(i, b)| {
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

fn main() {
    let args: Vec<i64> = std::env::args().skip(1).map(|a| a.parse().expect("integer")).collect();
    assert!(args.len() == 2, "usage: nbody n steps");
    let (n, steps) = (args[0] as usize, args[1]);
    let mut bs = init(n);
    for _ in 0..steps {
        bs = drift(&kick(&bs, 0.001), 0.001);
    }
    println!("{:.17}", energy(&bs));
}
