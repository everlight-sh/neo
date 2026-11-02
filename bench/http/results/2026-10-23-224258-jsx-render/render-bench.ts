import { render } from "./reference";
const iterations = Number(process.argv[2]);
if (!Number.isSafeInteger(iterations) || iterations <= 0) throw new Error("Positive iteration count required");
let checksum = 0;
for (let i = 0; i < iterations; i++) {
  const bytes = Buffer.from(render(i % 1000 + 1));
  for (let j = 0; j < bytes.length; j++) checksum += bytes[j];
}
console.log(checksum);
