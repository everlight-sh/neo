// Hand-rendered catalog page identical to React's renderToString output for
// bench/react/page.tsx. Idiomatic Rust SSR without a framework: a String
// built with push_str/write! and React's HTML escaping rules.
use std::fmt::Write;

const WORDS: [&str; 8] = ["Widget", "Gadget", "Gizmo", "Doohickey", "Sprocket", "Flange", "Bracket", "Grommet"];
const ADJ: [&str; 8] = ["Deluxe", "Basic", "Pro", "Mini", "Ultra", "Classic", "Eco", "Max"];

fn escape_into(out: &mut String, s: &str) {
    for c in s.chars() {
        match c {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            '"' => out.push_str("&quot;"),
            '\'' => out.push_str("&#x27;"),
            _ => out.push(c),
        }
    }
}

pub fn page(n: usize) -> String {
    let mut out = String::with_capacity(200 + n * 110);
    out.push_str("<!DOCTYPE html><html lang=\"en\"><head><title>Catalog</title></head><body><header><h1>Catalog</h1><p>");
    write!(out, "{} items", n).unwrap();
    out.push_str("</p></header><main><table><thead><tr><th>ID</th><th>Name</th><th>Price</th><th>Stock</th><th>Note</th></tr></thead><tbody>");
    let mut cents: u64 = 0;
    for i in 0..n {
        let dollars = (i * 37) % 1000;
        let stock = (i * 13) % 50;
        cents += (dollars as u64) * 100 + 99;
        out.push_str(if i % 2 == 1 { "<tr class=\"odd\"><td>" } else { "<tr class=\"even\"><td>" });
        write!(out, "{}</td><td>{} {}</td><td>${}.99</td><td>{}</td><td>", i, WORDS[i % 8], ADJ[(i * 7) % 8], dollars, stock).unwrap();
        if i % 5 == 0 { escape_into(&mut out, "Ben & Jerry's \"Special\" <limited>"); } else { out.push('-'); }
        out.push_str("</td></tr>");
    }
    write!(out, "</tbody></table></main><footer>Total: ${}.{:02}</footer></body></html>", cents / 100, cents % 100).unwrap();
    out
}

pub fn parse_page(path: &str) -> Result<usize, ()> {
    let n: usize = path.strip_prefix("/page/").ok_or(())?.parse().map_err(|_| ())?;
    if (1..=1000).contains(&n) { Ok(n) } else { Err(()) }
}
