// Production-style Rust: hyper 1 + tokio multi-threaded runtime.
#[path = "smooth.rs"]
mod smooth;
#[path = "nbody_seq.rs"]
mod nbody_seq;
#[path = "ssr.rs"]
mod ssr;
use http_body_util::BodyExt;
use hyper::Method;

#[derive(serde::Deserialize)]
struct NbodyReq { n: usize, steps: usize }
use std::convert::Infallible;
use std::net::SocketAddr;

use http_body_util::Full;
use hyper::body::{Bytes, Incoming};
use hyper::server::conn::http1;
use hyper::service::service_fn;
use hyper::{Request, Response, StatusCode};
use hyper_util::rt::TokioIo;
use tokio::net::TcpListener;

async fn hello(req: Request<Incoming>) -> Result<Response<Full<Bytes>>, Infallible> {
    if req.method() == Method::POST && req.uri().path() == "/nbody" {
        let bytes = req.into_body().collect().await.map(|b| b.to_bytes()).unwrap_or_default();
        let (status, ctype, body) = match serde_json::from_slice::<NbodyReq>(&bytes) {
            Ok(r) if (1..=4096).contains(&r.n) && r.steps <= 1000 => {
                let e = nbody_seq::simulate(r.n, r.steps);
                (StatusCode::OK, "application/json", Bytes::from(format!("{{\"n\":{},\"steps\":{},\"energy\":{:.9}}}", r.n, r.steps, e)))
            }
            _ => (StatusCode::BAD_REQUEST, "text/plain", Bytes::from_static(b"usage: POST /nbody {\"n\":1..4096,\"steps\":0..1000}")),
        };
        return Ok(Response::builder().status(status).header("Content-Type", ctype).body(Full::new(body)).unwrap());
    }
    let path = req.uri().path();
    let (status, ctype, body) = if path == "/" {
        (StatusCode::OK, "text/plain", Bytes::from_static(b"Hello, World!"))
    } else if path.starts_with("/page/") {
        match ssr::parse_page(path) {
            Ok(n) => (StatusCode::OK, "text/html; charset=utf-8", Bytes::from(ssr::page(n))),
            Err(()) => (StatusCode::BAD_REQUEST, "text/plain", Bytes::from_static(b"usage: /page/N, 1 <= N <= 1000")),
        }
    } else if path.starts_with("/smooth/") {
        match smooth::parse_smooth(path) {
            Ok(n) => (StatusCode::OK, "application/json", Bytes::from(smooth::json_body(n))),
            Err(()) => (StatusCode::BAD_REQUEST, "text/plain", Bytes::from_static(b"usage: /smooth/N, 1 <= N <= 1e6")),
        }
    } else {
        (StatusCode::NOT_FOUND, "text/plain", Bytes::from_static(b"Not Found"))
    };
    Ok(Response::builder()
        .status(status)
        .header("Content-Type", ctype)
        .body(Full::new(body))
        .unwrap())
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let port: u16 = std::env::args().nth(1).expect("port").parse()?;
    let listener = TcpListener::bind(SocketAddr::from(([0, 0, 0, 0], port))).await?;
    // Off by default in hyper; HYPER_PIPELINE_FLUSH=1 coalesces responses to pipelined requests.
    let pipeline_flush = std::env::var("HYPER_PIPELINE_FLUSH").is_ok();
    eprintln!("rust-hyper: serving on port {port} (pipeline_flush={pipeline_flush})");
    loop {
        let (stream, _) = listener.accept().await?;
        let _ = stream.set_nodelay(true);
        tokio::spawn(async move {
            let _ = http1::Builder::new()
                .pipeline_flush(pipeline_flush)
                .serve_connection(TokioIo::new(stream), service_fn(hello))
                .await;
        });
    }
}
