// Idiomatic parallel Rust: the same algorithm as examples/sieve.neo and
// bench/zig/sieve.zig. Sequential in-place marking, one byte per flag; the
// initial fill and the final count use rayon (Neo's parallel `arr`/`sum`).
use rayon::prelude::*;

fn main() {
    let args: Vec<usize> = std::env::args().skip(1).map(|a| a.parse().expect("integer")).collect();
    assert!(args.len() == 1, "usage: sieve n");
    let n = args[0];
    let mut marks: Vec<bool> = (0..n + 1).into_par_iter().map(|k| k >= 2).collect();
    let mut i = 2;
    while i <= n && i * i <= n {
        if marks[i] {
            // Slice iterator: no per-store bounds check.
            for m in marks[i * i..].iter_mut().step_by(i) {
                *m = false;
            }
        }
        i += 1;
    }
    let count = marks.par_iter().filter(|&&m| m).count();
    println!("{}", count);
}
