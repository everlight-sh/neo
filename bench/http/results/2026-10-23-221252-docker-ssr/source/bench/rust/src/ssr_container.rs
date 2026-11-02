// Same dynamic HTML as examples/jsx-ssr/page.tsx, using Hyper/Tokio.
use http_body_util::Full;
use hyper::body::{Bytes, Incoming};
use hyper::server::conn::http1;
use hyper::service::service_fn;
use hyper::{Method, Request, Response, StatusCode};
use hyper_util::rt::TokioIo;
use std::{convert::Infallible, net::SocketAddr};
use tokio::net::TcpListener;

fn escape(text: &str) -> String {
    let mut out = String::with_capacity(text.len() + 64);
    for c in text.chars() {
        match c {
            '&' => out.push_str("&amp;"), '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"), '"' => out.push_str("&quot;"),
            '\'' => out.push_str("&#x27;"), _ => out.push(c),
        }
    }
    out
}

fn render(count: u32) -> String {
    let name = escape(if count == 13 { "<script>alert(\"x\")</script> & ' café 🚀" }
        else { "Axon & React's \"JSX\" <components>" });
    let mut body = String::with_capacity(640);
    body.push_str("<!DOCTYPE html><html lang=\"en\"><head><title>JSX on Axon</title></head><body><main><h1>JSX on Axon</h1><article class=\"card\" title=\"");
    body.push_str(&name); body.push_str("\"><h2>"); body.push_str(&name);
    body.push_str("</h2><div><p>Hello, "); body.push_str(&name);
    let count_text = count.to_string();
    body.push_str("!</p><p data-count=\""); body.push_str(&count_text);
    body.push_str("\">Requests: "); body.push_str(&count_text); body.push_str("</p>");
    if count % 2 == 0 { body.push_str("<span class=\"badge\">Featured &amp; independent</span>"); }
    body.push_str(if count == 1 { "<p>One item" } else { "<p>Many items" });
    body.push_str("</p><p>Compiled components &amp; escaped props.</p></div></article></main><footer>No browser JavaScript required.</footer></body></html>");
    body
}

async fn handle(req: Request<Incoming>) -> Result<Response<Full<Bytes>>, Infallible> {
    let (status, content_type, body) = if req.method() != Method::GET {
        (StatusCode::METHOD_NOT_ALLOWED, "text/plain", Bytes::new())
    } else {
        let path = req.uri().path();
        if path != "/" && !path.starts_with("/page/") {
            (StatusCode::NOT_FOUND, "text/plain", Bytes::from_static(b"Not Found"))
        } else {
            let count = if path == "/" { Some(3) } else {
                let digits = &path[6..];
                if !digits.is_empty() && digits.len() <= 12 && digits.bytes().all(|b| b.is_ascii_digit()) {
                    digits.parse::<u64>().ok().filter(|n| (1..=1000).contains(n)).map(|n| n as u32)
                } else { None }
            };
            match count {
                Some(n) => (StatusCode::OK, "text/html; charset=utf-8", Bytes::from(render(n))),
                None => (StatusCode::BAD_REQUEST, "text/plain", Bytes::from_static(b"usage: /page/N, 1 <= N <= 1000")),
            }
        }
    };
    Ok(Response::builder().status(status).header("Content-Type", content_type)
        .body(Full::new(body)).unwrap())
}

fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let port: u16 = std::env::args().nth(1).unwrap_or_else(|| "8080".into()).parse()?;
    let workers: usize = std::env::var("BENCH_WORKERS").unwrap_or_else(|_| "1".into()).parse()?;
    let runtime = tokio::runtime::Builder::new_multi_thread().worker_threads(workers).enable_all().build()?;
    runtime.block_on(async move {
        let listener = TcpListener::bind(SocketAddr::from(([0, 0, 0, 0], port))).await?;
        eprintln!("rust: ready, rendering workers={workers}");
        loop {
            let (stream, _) = listener.accept().await?;
            stream.set_nodelay(true)?;
            tokio::spawn(async move {
                let _ = http1::Builder::new().pipeline_flush(true)
                    .serve_connection(TokioIo::new(stream), service_fn(handle)).await;
            });
        }
        #[allow(unreachable_code)]
        Ok::<(), Box<dyn std::error::Error + Send + Sync>>(())
    })
}
