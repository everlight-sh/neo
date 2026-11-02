// Idiomatic parallel Rust: rayon par_iter_mut over the output, ping-pong buffers.
use rayon::prelude::*;

fn stencil(xs: &[i64], out: &mut [i64]) {
    let n = xs.len();
    out.par_iter_mut().enumerate().for_each(|(i, o)| {
        *o = if i == 0 || i + 1 == n {
            xs[i]
        } else {
            (xs[i - 1] + 2 * xs[i] + xs[i + 1]) % 1000003
        };
    });
}

fn main() {
    let args: Vec<i64> = std::env::args().skip(1).map(|a| a.parse().expect("integer")).collect();
    assert!(args.len() == 2, "usage: stencil n iters");
    let (n, iters) = (args[0] as usize, args[1]);
    let mut a: Vec<i64> = (0..n).into_par_iter().map(|i| (i as i64 * 2654435761) % 1000003).collect();
    let mut b: Vec<i64> = vec![0; n];
    for _ in 0..iters {
        stencil(&a, &mut b);
        std::mem::swap(&mut a, &mut b);
    }
    let total: i64 = a.par_iter().sum();
    println!("{}", total);
}
