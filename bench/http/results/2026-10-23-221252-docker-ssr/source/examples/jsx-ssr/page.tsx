import type { ReactNode } from "react";

function Badge({ label }: { label: string }) {
  return <span className="badge">{label}</span>;
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return <article className="card" title={title}>
    <h2>{title}</h2>
    <div>{children}</div>
  </article>;
}

// This same source runs in React and compiles into native Axon functions.
export function Page({ name, count, featured }: { name: string; count: number; featured: boolean }) {
  return <html lang="en">
    <head><title>JSX on Axon</title></head>
    <body>
      <main>
        <h1>JSX on Axon</h1>
        <Card title={name}>
          <p>{`Hello, ${name}!`}</p>
          <p data-count={count}>Requests: {count}</p>
          {featured && <Badge label="Featured & independent" />}
          <p>{count === 1 ? "One item" : "Many items"}</p>
          <p>Compiled components &amp; escaped props.</p>
        </Card>
      </main>
      <footer>No browser JavaScript required.</footer>
    </body>
  </html>;
}
