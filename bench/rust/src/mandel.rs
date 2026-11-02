// Idiomatic parallel Rust: rayon over rows, iterator sum over columns.
use rayon::prelude::*;

fn escape(cx: f64, cy: f64, max: i64) -> i64 {
    let (mut zx, mut zy, mut k) = (0.0f64, 0.0f64, 0i64);
    while k < max && zx * zx + zy * zy <= 4.0 {
        let nx = zx * zx - zy * zy + cx;
        zy = 2.0 * zx * zy + cy;
        zx = nx;
        k += 1;
    }
    k
}

fn main() {
    let args: Vec<i64> = std::env::args().skip(1).map(|a| a.parse().expect("integer")).collect();
    assert!(args.len() == 3, "usage: mandel w h max");
    let (w, h, max) = (args[0], args[1], args[2]);
    let total: i64 = (0..h)
        .into_par_iter()
        .map(|y| {
            let cy = -1.5 + 3.0 * y as f64 / h as f64;
            (0..w).map(|x| escape(-2.0 + 3.0 * x as f64 / w as f64, cy, max)).sum::<i64>()
        })
        .sum();
    println!("{}", total);
}
