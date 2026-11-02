import { expect, test } from "bun:test";
import { compile } from "./compile";
import { readFileSync } from "node:fs";

const component = (expression: string, type = "string") =>
  `function Example({ value }: { value: ${type} }) { return ${expression}; }`;

test("shared React source generates ordinary Neo functions and escaped props", () => {
  const generated = compile(readFileSync(`${import.meta.dir}/page.tsx`, "utf8"));
  expect(generated).toContain("fn jsx_Page");
  expect(generated).toContain("fn jsx_Card");
  expect(generated).not.toContain("jsx_Card(p_name");
  expect(generated).toContain("escape(p_title)");
  expect(generated).toContain('if p_featured then');
  expect(generated).not.toContain("extern");
});

test("fragments, comments, entities, numeric props, null and ternaries", () => {
  const generated = compile(component('<><p title="a &quot;quote&quot;">A &amp; B &#x1f680;</p>{/* ignored */}{value >= 2 ? value : null}<br /></>', "number"));
  expect(generated).toContain('A &amp; B 🚀');
  expect(generated).toContain("utoa(p_value)");
  expect(generated).toContain('<br/>');
});

const rejected: [string, string][] = [
  ['import { useState } from "react"; ' + component('<p>{value}</p>'), "runtime imports"],
  ['function Example({ value }: {value:string}) { const x = useState(0); return <p>{x}</p>; }', "one return expression"],
  [component('<p>{value.toUpperCase()}</p>'), "Unsupported CallExpression"],
  [component('<p onClick={value}>x</p>'), "Unsupported HTML attribute onClick"],
  [component('<p dangerouslySetInnerHTML={value} />'), "Unsupported HTML attribute"],
  [component('<p style={value} />'), "Unsupported HTML attribute style"],
  [component('<a href={value}>x</a>'), "Unsupported HTML tag"],
  [component('<p {...value} />'), "Spread attributes"],
  [component('<p title="one" title="two" />'), "Duplicate prop"],
  [component('<p>{missing}</p>'), "Unknown prop missing"],
  [component('<p>{value + 1}</p>', "number"), "Only integer comparisons"],
  ['function A({key}:{key:string}) {return <p>{key}</p>;}', "Reserved React props"],
  ['function A({children}:{children:string}) {return <p>{children}</p>;}', "Declare children as ReactNode"],
  [component('<p>{value && <span />}</p>', "number"), "must be boolean"],
  [component('<p>{-1}</p>'), "Unsupported PrefixUnaryExpression"],
  [component('<p>{1.25}</p>'), "safe integer"],
  [component('<p>&copy;</p>'), "Unsupported JSX entity"],
  [component('<Missing value={value} />'), "unknown component"],
  [component('<Example value={value} />'), "Recursive component cycles"],
  ['function A({value}:{value:string}) {return <B value={value}/>;} function B({value}:{value:string}) {return <A value={value}/>;}', "Recursive component cycles"],
  ['function A({value}:{value:string}) {return <p/>;} function B({value}:{value:string}) {return <A/>;}', "Missing required prop"],
  ['function A({value}:{value:string}) {return <p/>;} function B({value}:{value:boolean}) {return <A value={value}/>;}', "expects text"],
  ['function A({value}:{value:string}) {return <p/>;} function B({value}:{value:string}) {return <A value={value}>child</A>;}', "does not accept children"],
];
for (const [source, diagnostic] of rejected) test(`reject: ${diagnostic}`, () => {
  expect(() => compile(source, "rejected.tsx")).toThrow(diagnostic);
});

test("diagnostics include the source location", () => {
  expect(() => compile(component('<p>{window}</p>'), "my-page.tsx")).toThrow(/my-page\.tsx:1:\d+:/);
});

test("JavaScript control characters become valid Neo byte escapes", () => {
  const generated = compile(component('<p>{"\\u0000\\b\\f\\n\\t\\\\u0000"}</p>'));
  expect(generated).toContain('\\x00\\x08\\x0c\\x0a\\x09');
  expect(generated).toContain('\\\\u0000');
});

test("literal attribute spacing is preserved", () => {
  expect(compile(component('<p title="one  two" />'))).toContain('one  two');
});

test("optimizations have an explicit baseline mode", () => {
  const source = readFileSync(`${import.meta.dir}/page.tsx`, "utf8");
  const baseline = compile(source, "page.tsx", { optimize: false });
  expect(baseline).toContain("jsx_Card(p_name");
  expect(baseline).toContain("escape(utoa(p_count))");
  expect(baseline).not.toContain("let jsx_cached");
});

test("static markup is coalesced, dynamic text escaped once, numbers formatted once", () => {
  const generated = compile(readFileSync(`${import.meta.dir}/page.tsx`, "utf8")).split("fn jsx_Page")[1];
  expect(generated.match(/escape\(p_name\)/g)).toHaveLength(1);
  expect(generated.match(/utoa\(p_count\)/g)).toHaveLength(1);
  expect(generated).toContain("<html lang=");
  expect(generated).not.toContain("escape(utoa");
  expect(generated).not.toContain('escape(concat("Hello');
});

test("sharing never hoists conditional escaping out of its branch", () => {
  const generated = compile('function A({text,show}:{text:string;show:boolean}) {return <>{show && <p>{text}{text}</p>}</>;}');
  expect(generated).toContain('if p_show then concat');
  expect(generated).not.toContain('let jsx_cached');
});
