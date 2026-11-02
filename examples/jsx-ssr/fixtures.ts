import { render } from "./reference";
// React is a test/build tool here. The native executable reads none of this.
console.log(JSON.stringify(Object.fromEntries(Array.from({ length: 1000 }, (_, i) => [i + 1, render(i + 1)]))));
