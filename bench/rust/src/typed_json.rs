// Typed versus dynamic serde_json on the same inputs as examples/library_bench.neo
// (small document) and bench/core/orders_json.neo (1,000-order array).
use serde::Deserialize;
use serde_json::Value;

#[derive(Deserialize)]
struct Document { id: u64, name: String, #[allow(dead_code)] active: bool, values: Vec<i64> }

#[derive(Deserialize)]
struct Order { customer: i64, qty: i64, price: i64, name: String }

fn orders_text(n: i64) -> String {
    let rows: Vec<String> = (0..n).map(|i| format!("{{\"customer\":{},\"qty\":{},\"price\":3,\"name\":\"user{}\"}}", i % 8, i % 17, i)).collect();
    format!("[{}]", rows.join(","))
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mode = args[1].as_str();
    let n: i64 = args[2].parse().expect("count");
    let mut sum: i64 = 0;
    match mode {
        // Small document, built per iteration as in library_bench.neo.
        "doc-value" | "doc-typed" => for i in 0..n {
            let source = format!("{{\"id\":{},\"name\":\"café 🚀\",\"active\":true,\"values\":[1,2,3]}}", i % 1000);
            sum += if mode == "doc-value" {
                let v: Value = serde_json::from_str(&source).unwrap();
                v["id"].as_i64().unwrap() + v["name"].as_str().unwrap().len() as i64 + v["values"].as_array().unwrap().len() as i64 + 1
            } else {
                let d: Document = serde_json::from_str(&source).unwrap();
                d.id as i64 + d.name.len() as i64 + d.values.len() as i64 + 1
            };
        },
        // 1,000-order array built once, decoded n times.
        "orders-value" | "orders-typed" => {
            let text = orders_text(1000);
            for _ in 0..n {
                sum += if mode == "orders-value" {
                    let v: Value = serde_json::from_str(&text).unwrap();
                    v.as_array().unwrap().iter().map(|r| r["qty"].as_i64().unwrap() * r["price"].as_i64().unwrap() + r["customer"].as_i64().unwrap() + r["name"].as_str().unwrap().len() as i64).sum::<i64>()
                } else {
                    let rows: Vec<Order> = serde_json::from_str(&text).unwrap();
                    rows.iter().map(|r| r.qty * r.price + r.customer + r.name.len() as i64).sum::<i64>()
                };
            }
        }
        // Stage splits: building the small document only, and decoding a fixed one.
        "doc-build" => for i in 0..n { sum += format!("{{\"id\":{},\"name\":\"café 🚀\",\"active\":true,\"values\":[1,2,3]}}", i % 1000).len() as i64; },
        "doc-fixed-typed" => { let source = "{\"id\":7,\"name\":\"café 🚀\",\"active\":true,\"values\":[1,2,3]}".to_string();
            for _ in 0..n { let d: Document = serde_json::from_str(std::hint::black_box(&source)).unwrap(); sum += d.id as i64 + d.name.len() as i64 + d.values.len() as i64 + 1; } },
        _ => panic!("mode"),
    }
    println!("{sum}");
}
