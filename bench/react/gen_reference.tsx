import { render } from "./page";
process.stdout.write(render(Number(process.argv[2] ?? 50)));
