// Matching React components for examples/ssr.neo. Rendered anew per request.
import { renderToString } from "react-dom/server";

const WORDS = ["Widget", "Gadget", "Gizmo", "Doohickey", "Sprocket", "Flange", "Bracket", "Grommet"];
const ADJ = ["Deluxe", "Basic", "Pro", "Mini", "Ultra", "Classic", "Eco", "Max"];

function Row({ i }: { i: number }) {
  const dollars = (i * 37) % 1000;
  const stock = (i * 13) % 50;
  const note = i % 5 === 0 ? `Ben & Jerry's "Special" <limited>` : "-";
  return (
    <tr className={i % 2 === 1 ? "odd" : "even"}>
      <td>{i}</td>
      <td>{`${WORDS[i % 8]} ${ADJ[(i * 7) % 8]}`}</td>
      <td>{`$${dollars}.99`}</td>
      <td>{stock}</td>
      <td>{note}</td>
    </tr>
  );
}

function Page({ n }: { n: number }) {
  const rows = [];
  let cents = 0;
  for (let i = 0; i < n; i++) {
    rows.push(<Row key={i} i={i} />);
    cents += ((i * 37) % 1000) * 100 + 99;
  }
  const total = `${Math.floor(cents / 100)}.${String(cents % 100).padStart(2, "0")}`;
  return (
    <html lang="en">
      <head><title>Catalog</title></head>
      <body>
        <header><h1>Catalog</h1><p>{`${n} items`}</p></header>
        <main>
          <table>
            <thead><tr><th>ID</th><th>Name</th><th>Price</th><th>Stock</th><th>Note</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </main>
        <footer>{`Total: $${total}`}</footer>
      </body>
    </html>
  );
}

export function render(n: number): string {
  return "<!DOCTYPE html>" + renderToString(<Page n={n} />);
}
