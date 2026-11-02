// GET with reqwest COUNT times: fetch-client PORT PATH COUNT SIZE KEEP [CA.pem].
// KEEP 0 opens a connection per request, like fetch.neo; KEEP 1 reuses one.
// With a root certificate the requests use HTTPS. Prints the total
// nanoseconds and how many responses were 200 with SIZE bytes, then each
// request's nanoseconds.
use std::time::{Duration, Instant};

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let count: usize = args[3].parse().unwrap();
    let size: usize = args[4].parse().unwrap();
    let mut builder = reqwest::blocking::Client::builder().timeout(Duration::from_secs(10));
    if args[5] != "1" {
        builder = builder.pool_max_idle_per_host(0);
    }
    let scheme = match args.get(6) {
        Some(ca) => {
            let pem = std::fs::read(ca).unwrap();
            builder = builder.add_root_certificate(reqwest::Certificate::from_pem(&pem).unwrap());
            "https"
        }
        None => "http",
    };
    let client = builder.build().unwrap();
    let url = format!("{}://127.0.0.1:{}{}", scheme, args[1], args[2]);
    let mut times = Vec::with_capacity(count);
    let mut good = 0;
    let start = Instant::now();
    for _ in 0..count {
        let before = Instant::now();
        let ok = match client.get(&url).send() {
            Ok(response) => {
                let status = response.status().as_u16();
                matches!(response.bytes(), Ok(body) if status == 200 && body.len() == size)
            }
            Err(_) => false,
        };
        times.push(before.elapsed().as_nanos().to_string());
        if ok {
            good += 1;
        }
    }
    println!("{} {}", start.elapsed().as_nanos(), good);
    println!("{}", times.join(" "));
}
