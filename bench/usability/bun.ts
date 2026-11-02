import { readFileSync, openSync, writeSync, fsyncSync, closeSync } from "node:fs";
try {
  const args=process.argv.slice(2);
  if(args[0]==="parse") {
    const count=Number(args[1]);let sum=0;
    for(let i=0;i<count;i++) {
      const value=JSON.parse(`{"id":${i%1000},"name":"café 🚀","active":true,"values":[1,2,3]}`);
      sum+=value.id+Buffer.byteLength(value.name)+value.values.length+1;
    }
    console.log(sum);
  } else {
    if(args.length!==2&&args.length!==3)throw Error("usage: INPUT OUTPUT [MIN_SCORE]");
    const minimum=Number(args[2]??"0"), rows=JSON.parse(readFileSync(args[0],"utf8"));
    if(!Array.isArray(rows)||!Number.isSafeInteger(minimum)||rows.some(row=>!row||!Number.isSafeInteger(row.id)||!Number.isSafeInteger(row.score)||typeof row.name!=="string"))throw Error("invalid records");
    const selected=rows.filter(row=>row.score>=minimum).sort((a,b)=>a.score-b.score);
    const fd=openSync(args[1],"w");try{const bytes=Buffer.from(JSON.stringify(selected)+"\n");let offset=0;while(offset<bytes.length)offset+=writeSync(fd,bytes,offset);fsyncSync(fd)}finally{closeSync(fd)}
  }
} catch(error) {console.error("bun-json:",String(error));process.exit(2)}
