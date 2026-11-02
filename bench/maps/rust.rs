use std::collections::HashMap;
use std::io::{self,Read,Write};
use std::time::Instant;
fn checkpoint(phase:&str,ns:u128,checksum:u64,count:usize) {
    println!("{phase} {ns} {checksum} {count}");io::stdout().flush().unwrap();
    let mut ack=[0u8;1];io::stdin().read_exact(&mut ack).unwrap();
}
fn lookup(map:&HashMap<String,String>,n:usize,multiplier:u64,remaining:bool)->u64 {
    let mut checksum=0;
    for i in 0..n {
        let key=i.to_string();
        if remaining && i%2==0 {assert!(map.get(&key).is_none());}
        else {let value=map.get(&key).unwrap();let parsed=value.parse::<u64>().unwrap();assert_eq!(parsed,i as u64*multiplier);checksum+=parsed;}
    }
    checksum
}
fn main() {
    let args:Vec<String>=std::env::args().collect();let n=args[1].parse::<usize>().unwrap();let reserved=args[2]!="0";
    let start=Instant::now();let mut map=if reserved {HashMap::with_capacity(n)} else {HashMap::new()};
    for i in 0..n {map.insert(i.to_string(),(i*7).to_string());}
    let ns=start.elapsed().as_nanos();assert_eq!(map.len(),n);checkpoint("insert",ns,0,map.len());
    let start=Instant::now();let sum=lookup(&map,n,7,false);checkpoint("lookup",start.elapsed().as_nanos(),sum,map.len());
    checkpoint("steady",0,sum,map.len());
    let start=Instant::now();for i in 0..n {map.insert(i.to_string(),(i*11).to_string());}checkpoint("update",start.elapsed().as_nanos(),0,map.len());
    let start=Instant::now();let sum=lookup(&map,n,11,false);checkpoint("lookup_updated",start.elapsed().as_nanos(),sum,map.len());
    let start=Instant::now();for i in (0..n).step_by(2) {map.remove(&i.to_string());}checkpoint("delete",start.elapsed().as_nanos(),0,map.len());
    let start=Instant::now();let sum=lookup(&map,n,11,true);checkpoint("lookup_remaining",start.elapsed().as_nanos(),sum,map.len());
    std::hint::black_box(&map);
}
