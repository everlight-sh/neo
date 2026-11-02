import { readSync, writeSync } from "node:fs";
const n = Number(process.argv[2]);
if (process.argv[3] !== "0") throw Error("Bun Map has no reserve API; only growing mode is measured");
const input = Buffer.alloc(1);
function checkpoint(phase: string, elapsed: bigint, checksum: number, count: number) {
  writeSync(1, `${phase} ${elapsed} ${checksum} ${count}\n`);
  if (readSync(0, input, 0, 1, null) !== 1) throw Error("acknowledgement missing");
}
function lookup(map: Map<string,string>, multiplier: number, remaining: boolean) {
  let sum = 0;
  for (let i=0;i<n;i++) {
    const value=map.get(String(i));
    if (remaining && i%2===0) { if (value!==undefined) throw Error("present"); }
    else {
      if (value===undefined || Number(value)!==i*multiplier) throw Error("value");
      sum+=Number(value);
    }
  }
  return sum;
}
let start=process.hrtime.bigint();
const map=new Map<string,string>();
for (let i=0;i<n;i++) map.set(String(i),String(i*7));
checkpoint("insert",process.hrtime.bigint()-start,0,map.size);
start=process.hrtime.bigint(); let sum=lookup(map,7,false);
checkpoint("lookup",process.hrtime.bigint()-start,sum,map.size);
Bun.gc(true); checkpoint("steady",0n,sum,map.size);
start=process.hrtime.bigint(); for (let i=0;i<n;i++) map.set(String(i),String(i*11));
checkpoint("update",process.hrtime.bigint()-start,0,map.size);
start=process.hrtime.bigint(); sum=lookup(map,11,false);
checkpoint("lookup_updated",process.hrtime.bigint()-start,sum,map.size);
start=process.hrtime.bigint(); for (let i=0;i<n;i+=2) map.delete(String(i));
checkpoint("delete",process.hrtime.bigint()-start,0,map.size);
start=process.hrtime.bigint(); sum=lookup(map,11,true);
checkpoint("lookup_remaining",process.hrtime.bigint()-start,sum,map.size);
