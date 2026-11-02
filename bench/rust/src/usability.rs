use std::{fs::File,io::{Read,Write}};
use serde_json::Value;

fn run()->Result<(),Box<dyn std::error::Error>> {
    let args:Vec<String>=std::env::args().collect();
    if args.get(1).map(String::as_str)==Some("parse") {
        let count:u64=args.get(2).ok_or("iterations")?.parse()?;let mut sum=0u64;
        for i in 0..count {
            let source=format!("{{\"id\":{},\"name\":\"café 🚀\",\"active\":true,\"values\":[1,2,3]}}",i%1000);
            let value:Value=serde_json::from_str(&source)?;
            sum+=value["id"].as_u64().ok_or("id")?+value["name"].as_str().ok_or("name")?.len() as u64+value["values"].as_array().ok_or("values")?.len() as u64+1;
        }
        println!("{sum}");return Ok(())
    }
    if !(args.len()==3||args.len()==4) {return Err("usage: INPUT OUTPUT [MIN_SCORE]".into())}
    let minimum:i64=args.get(3).map(String::as_str).unwrap_or("0").parse()?;
    let mut source=String::new();File::open(&args[1])?.read_to_string(&mut source)?;
    let value:Value=serde_json::from_str(&source)?;
    let mut rows=value.as_array().ok_or("expected array")?.clone();
    for row in &rows {
        if row.get("id").and_then(Value::as_i64).is_none()||row.get("score").and_then(Value::as_i64).is_none()||row.get("name").and_then(Value::as_str).is_none() {
            return Err("invalid record".into())
        }
    }
    rows.retain(|row|row["score"].as_i64().unwrap()>=minimum);
    rows.sort_by_key(|row|row["score"].as_i64().unwrap());
    let mut output=File::create(&args[2])?;
    serde_json::to_writer(&mut output,&rows)?;output.write_all(b"\n")?;output.sync_all()?;
    Ok(())
}
fn main(){if let Err(error)=run(){eprintln!("rust-json: {error}");std::process::exit(2)}}
