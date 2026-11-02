// "Simple HTTP server" the way the Rust Book does it: std::net, one thread per
// connection, hand-written HTTP/1.1 framing with keep-alive. No dependencies.
#[path = "smooth.rs"]
mod smooth;
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::thread;

const OK: &[u8] = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 13\r\n\r\nHello, World!";
const NOT_FOUND: &[u8] = b"HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\nContent-Length: 9\r\n\r\nNot Found";
const BAD: &[u8] = b"HTTP/1.1 400 Bad Request\r\nContent-Type: text/plain\r\nContent-Length: 31\r\n\r\nusage: /smooth/N, 1 <= N <= 1e6";

fn respond(head: &[u8]) -> Vec<u8> {
    // request line: METHOD SP PATH SP VERSION
    let line_end = head.iter().position(|&b| b == b'\r').unwrap_or(head.len());
    let mut parts = head[..line_end].split(|&b| b == b' ');
    let method = parts.next().unwrap_or(b"");
    let path = std::str::from_utf8(parts.next().unwrap_or(b"")).unwrap_or("");
    if method != b"GET" { return NOT_FOUND.to_vec(); }
    if path == "/" { return OK.to_vec(); }
    if path.starts_with("/smooth/") {
        return match smooth::parse_smooth(path) {
            Ok(n) => {
                let body = smooth::json_body(n);
                format!("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\n\r\n{}", body.len(), body).into_bytes()
            }
            Err(()) => BAD.to_vec(),
        };
    }
    NOT_FOUND.to_vec()
}

fn find(hay: &[u8], needle: &[u8]) -> Option<usize> {
    hay.windows(needle.len()).position(|w| w == needle)
}

fn header_value<'a>(head: &'a [u8], name: &str) -> Option<&'a [u8]> {
    for line in head.split(|&b| b == b'\n') {
        if line.len() > name.len()
            && line[name.len()] == b':'
            && line[..name.len()].eq_ignore_ascii_case(name.as_bytes())
        {
            let v = &line[name.len() + 1..];
            let v = v.strip_suffix(b"\r").unwrap_or(v);
            return Some(v.trim_ascii());
        }
    }
    None
}

fn handle(mut stream: TcpStream) {
    let _ = stream.set_nodelay(true);
    let mut buf = vec![0u8; 65536];
    let mut have = 0usize;
    loop {
        let Some(end) = find(&buf[..have], b"\r\n\r\n") else {
            if have == buf.len() { return; }
            match stream.read(&mut buf[have..]) { Ok(0) | Err(_) => return, Ok(n) => have += n }
            continue;
        };
        let hdr = end + 4;
        let body: usize = header_value(&buf[..hdr], "Content-Length")
            .and_then(|v| std::str::from_utf8(v).ok())
            .and_then(|v| v.parse().ok())
            .unwrap_or(0);
        if hdr + body > buf.len() { return; }
        if have < hdr + body {
            match stream.read(&mut buf[have..]) { Ok(0) | Err(_) => return, Ok(n) => have += n }
            continue;
        }
        let close = header_value(&buf[..hdr], "Connection").map_or(false, |v| v.eq_ignore_ascii_case(b"close"));
        let resp = respond(&buf[..hdr]);
        if stream.write_all(&resp).is_err() || close { return; }
        let used = hdr + body;
        buf.copy_within(used..have, 0);
        have -= used;
    }
}

fn main() {
    let port = std::env::args().nth(1).expect("port");
    let listener = TcpListener::bind(format!("0.0.0.0:{port}")).expect("bind");
    eprintln!("rust-std: serving on port {port}");
    for stream in listener.incoming() {
        if let Ok(s) = stream { thread::spawn(move || handle(s)); }
    }
}
