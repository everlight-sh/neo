// Shared compute for the /smooth/N endpoint: 32 passes of a 3-point stencil
// over a synthetic signal, then a checksum. Written the way one writes it in
// Rust: Vec<i64>, indexing, ping-pong buffers.
pub const PASSES: usize = 32;

pub fn stencil(xs: &[i64], out: &mut [i64]) {
    let n = xs.len();
    for i in 0..n {
        out[i] = if i == 0 || i + 1 == n {
            xs[i]
        } else {
            (xs[i - 1] + 2 * xs[i] + xs[i + 1]) % 1000003
        };
    }
}

pub fn checksum(n: usize) -> i64 {
    let mut a: Vec<i64> = (0..n).map(|i| (i as i64 * 2654435761) % 1000003).collect();
    let mut b = vec![0i64; n];
    for _ in 0..PASSES {
        stencil(&a, &mut b);
        std::mem::swap(&mut a, &mut b);
    }
    a.iter().sum()
}

/// Parses "/smooth/N"; Ok(n) for 1..=1_000_000, Err(()) otherwise.
pub fn parse_smooth(path: &str) -> Result<usize, ()> {
    let n: usize = path.strip_prefix("/smooth/").ok_or(())?.parse().map_err(|_| ())?;
    if (1..=1_000_000).contains(&n) { Ok(n) } else { Err(()) }
}

pub fn json_body(n: usize) -> String {
    format!("{{\"n\":{},\"passes\":{},\"checksum\":{}}}", n, PASSES, checksum(n))
}
