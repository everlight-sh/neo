// Same output as the shared TSX page, with direct string rendering in Bun.
const escape = (text: string) => text.replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#x27;" })[c]!);
export function render(count: number): string {
  const name = escape(count === 13 ? '<script>alert("x")</script> & \' café 🚀' : 'Axon & React\'s "JSX" <components>');
  return '<!DOCTYPE html><html lang="en"><head><title>JSX on Axon</title></head><body><main><h1>JSX on Axon</h1><article class="card" title="' + name + '"><h2>' + name + '</h2><div><p>Hello, ' + name + `!</p><p data-count="${count}">Requests: ${count}</p>` +
    (count % 2 === 0 ? '<span class="badge">Featured &amp; independent</span>' : '') +
    (count === 1 ? '<p>One item' : '<p>Many items') +
    '</p><p>Compiled components &amp; escaped props.</p></div></article></main><footer>No browser JavaScript required.</footer></body></html>';
}
