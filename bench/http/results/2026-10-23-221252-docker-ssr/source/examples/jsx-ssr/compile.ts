// Example-only frontend. Nothing here is imported by axonc or the runtime.
import ts from "typescript";

type Kind = "text" | "number" | "boolean" | "html" | "empty";
type Value = { kind: Kind; code: string };
type Prop = { name: string; kind: Kind };
// Axon accepts byte escapes (\xNN), rather than JavaScript's \uNNNN escapes.
// The UTF-8 round trip matches HTTP's replacement of lone UTF-16 surrogates.
const quote = (s: string) => '"' + [...Buffer.from(s).toString("utf8")].map(c =>
  c === "\\" ? "\\\\" : c === '"' ? '\\"' : c.codePointAt(0)! < 32 ? `\\x${c.charCodeAt(0).toString(16).padStart(2, "0")}` : c).join("") + '"';
const concat = (parts: string[]) => parts.length ? parts.length === 1 ? parts[0] : `concat(${parts.join(", ")})` : '""';
const tags = new Set("html head title body main section article header footer h1 h2 h3 p span div strong em ul ol li br hr".split(" "));
const voidTags = new Set(["br", "hr"]);

export function compile(source: string, filename = "page.tsx", options: { optimize?: boolean } = {}): string {
  const optimize = options.optimize !== false;
  // Keep fragment structure until emission: flatten concatenations, coalesce
  // literal markup, and escape static text during the build, not each request.
  const constants = new Map<string, string>();
  const sequences = new Map<string, string[]>();
  const choices = new Map<string, { cond: string; yes: string; no: string }>();
  const safeNumbers = new Set<string>();
  const literal = (s: string) => {
    const code = quote(s);
    constants.set(code, Buffer.from(s).toString("utf8"));
    return code;
  };
  literal("");
  const join = (parts: string[]): string => {
    if (!optimize) return concat(parts);
    const flat: string[] = [];
    for (const part of parts.flatMap(p => sequences.get(p) ?? [p])) {
      const text = constants.get(part);
      if (text === "") continue;
      const previous = flat.length ? constants.get(flat[flat.length - 1]) : undefined;
      if (text !== undefined && previous !== undefined) flat[flat.length - 1] = literal(previous + text);
      else flat.push(part);
    }
    const code = flat.length ? concat(flat) : literal("");
    if (flat.length > 1) sequences.set(code, flat);
    return code;
  };
  const choice = (cond: string, yes: string, no: string) => {
    const code = `(if ${cond} then ${yes} else ${no})`;
    choices.set(code, { cond, yes, no });
    return code;
  };
  const escapeLiteral = (s: string) => s.replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#x27;" })[c]!);
  const escaped = (code: string): string => {
    if (!optimize) return `escape(${code})`;
    const text = constants.get(code);
    if (text !== undefined) return literal(escapeLiteral(text));
    if (safeNumbers.has(code)) return code;
    const parts = sequences.get(code);
    if (parts) return join(parts.map(escaped));
    const branch = choices.get(code);
    if (branch) return choice(branch.cond, escaped(branch.yes), escaped(branch.no));
    return `escape(${code})`;
  };
  // Share repeated dynamic fragments only when they are unconditional pieces
  // of the result. Never hoist work out of an unselected branch.
  const finish = (code: string): string => {
    if (!optimize) return code;
    const parts = sequences.get(code);
    if (!parts) return code;
    const counts = new Map<string, number>();
    for (const part of parts) if (/^(?:escape|utoa)\(/.test(part)) counts.set(part, (counts.get(part) ?? 0) + 1);
    const shared = [...counts].filter(([, count]) => count > 1).map(([code], i) => ({ code, name: `jsx_cached${i}` }));
    const names = new Map(shared.map(s => [s.code, s.name]));
    return shared.map(s => `let ${s.name} = ${s.code} in\n    `).join("") + join(parts.map(p => names.get(p) ?? p));
  };
  const file = ts.createSourceFile(filename, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const fail = (node: ts.Node, message: string): never => {
    const { line, character } = file.getLineAndCharacterOfPosition(node.getStart(file));
    throw new Error(`${filename}:${line + 1}:${character + 1}: ${message}`);
  };
  const diagnostics = (file as any).parseDiagnostics as ts.Diagnostic[];
  if (diagnostics.length) throw new Error(`${filename}: ${ts.flattenDiagnosticMessageText(diagnostics[0].messageText, " ")}`);
  const identifier = (node: ts.Node) => {
    if (!ts.isIdentifier(node) || !/^[A-Za-z][A-Za-z0-9_]*$/.test(node.text)) fail(node, "Expected a simple identifier");
    return (node as ts.Identifier).text;
  };
  const components = new Map<string, { node: ts.FunctionDeclaration; props: Prop[]; body: ts.Expression }>();
  for (const node of file.statements) {
    if (ts.isImportDeclaration(node)) {
      const clause = node.importClause;
      if (!ts.isStringLiteral(node.moduleSpecifier) || node.moduleSpecifier.text !== "react" || !clause?.isTypeOnly ||
          clause.name || !clause.namedBindings || !ts.isNamedImports(clause.namedBindings) ||
          clause.namedBindings.elements.some(e => e.name.text !== "ReactNode" || !!e.propertyName)) {
        fail(node, "Only import type { ReactNode } from 'react' is supported; runtime imports are not translated");
      }
      continue;
    }
    if (!ts.isFunctionDeclaration(node) || !node.name || !node.body || node.asteriskToken || node.typeParameters ||
        node.modifiers?.some(m => m.kind !== ts.SyntaxKind.ExportKeyword) || node.parameters.length !== 1) {
      fail(node, "Only synchronous function components with one destructured, typed props argument are supported");
    }
    const fn = node as ts.FunctionDeclaration;
    const name = identifier(fn.name!);
    if (!/^[A-Z]/.test(name) || components.has(name)) fail(node, "Component names must be unique and start with a capital letter");
    const arg = fn.parameters[0];
    if (!ts.isObjectBindingPattern(arg.name) || !arg.type || !ts.isTypeLiteralNode(arg.type) || arg.initializer || arg.dotDotDotToken) {
      fail(arg, "Use inline props types: ({ name }: { name: string })");
    }
    const props: Prop[] = (arg.type as ts.TypeLiteralNode).members.map(member => {
      if (!ts.isPropertySignature(member) || !member.type || member.questionToken || member.modifiers) fail(member, "Only required props are supported");
      const prop = member as ts.PropertySignature;
      const type = prop.type!;
      const kind: Kind = type.kind === ts.SyntaxKind.StringKeyword ? "text" :
        type.kind === ts.SyntaxKind.NumberKeyword ? "number" : type.kind === ts.SyntaxKind.BooleanKeyword ? "boolean" :
        ts.isTypeReferenceNode(type) && type.typeName.getText(file) === "ReactNode" && !type.typeArguments ? "html" :
        fail(type, "Props must be string, number (nonnegative integer), boolean, or ReactNode");
      const name = identifier(prop.name);
      if (name === "key" || name === "ref") fail(prop, "Reserved React props key and ref are unsupported");
      if (name === "children" && kind !== "html") fail(prop, "Declare children as ReactNode");
      return { name, kind };
    });
    const bindings = (arg.name as ts.ObjectBindingPattern).elements.map(e => {
      if (e.propertyName || e.initializer || e.dotDotDotToken) fail(e, "Renamed, default, and rest props are not supported");
      return identifier(e.name);
    });
    if (new Set(bindings).size !== bindings.length || new Set(props.map(p => p.name)).size !== props.length ||
        bindings.length !== props.length || props.some(p => !bindings.includes(p.name))) fail(arg, "Destructure every declared prop exactly once");
    const statements = fn.body!.statements;
    if (statements.length !== 1 || !ts.isReturnStatement(statements[0]) || !statements[0].expression) {
      fail(fn.body!, "Component bodies must contain one return expression; hooks and arbitrary JavaScript are unsupported");
    }
    components.set(name, { node: fn, props, body: (statements[0] as ts.ReturnStatement).expression! });
  }
  if (!components.size) throw new Error(`${filename}: no components found`);
  // Reject cycles: this frontend does not implement recursive components.
  const edges = new Map<string, Set<string>>();
  let current = "";
  let scope = new Map<string, Value>();
  const expansion: string[] = [];
  let expansionBudget = 0;
  const asText = (v: Value, node: ts.Node): string => {
    if (v.kind === "text") return v.code;
    if (v.kind !== "number") return fail(node, "Expected string or nonnegative integer");
    const code = `utoa(${v.code})`;
    safeNumbers.add(code);
    return code;
  };
  const render = (v: Value, node: ts.Node): string => v.kind === "html" ? v.code : v.kind === "empty" || v.kind === "boolean" ? literal("") : escaped(asText(v, node));
  const decode = (s: string, node: ts.Node): string => s.replace(/&([^;\s]+);/g, (_, entity: string) => {
    const known: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'" };
    if (entity in known) return known[entity];
    if (/^#(?:[0-9]+|x[0-9a-f]+)$/i.test(entity)) {
      const n = entity[1].toLowerCase() === "x" ? parseInt(entity.slice(2), 16) : Number(entity.slice(1));
      if (n > 0 && n <= 0x10ffff && !(n >= 0xd800 && n <= 0xdfff)) return String.fromCodePoint(n);
    }
    return fail(node, `Unsupported JSX entity &${entity};`);
  });
  const text = (node: ts.JsxText): string => {
    const lines = node.text.split(/\r\n|\n|\r/);
    let last = -1;
    lines.forEach((line, i) => { if (/[^ \t]/.test(line)) last = i; });
    return decode(lines.map((line, i) => {
      line = line.replace(/\t/g, " ");
      if (i !== 0) line = line.replace(/^ +/, "");
      if (i !== lines.length - 1) line = line.replace(/ +$/, "");
      return line ? line + (i !== last ? " " : "") : "";
    }).join(""), node);
  };
  const children = (nodes: ts.NodeArray<ts.JsxChild>) => join(nodes.map(n => render(value(n), n)));
  const value = (node: ts.Node): Value => {
    if (ts.isParenthesizedExpression(node)) return value(node.expression);
    if (ts.isJsxExpression(node)) return node.expression ? value(node.expression) : { kind: "empty", code: '""' };
    if (ts.isJsxText(node)) return { kind: "text", code: literal(text(node)) };
    if (ts.isJsxFragment(node)) return { kind: "html", code: children(node.children) };
    if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) return { kind: "text", code: literal(node.text) };
    if (ts.isNumericLiteral(node)) {
      if (!Number.isSafeInteger(Number(node.text)) || Number(node.text) < 0) fail(node, "Only nonnegative safe integer literals are supported");
      return { kind: "number", code: String(Number(node.text)) };
    }
    if (node.kind === ts.SyntaxKind.TrueKeyword || node.kind === ts.SyntaxKind.FalseKeyword) return { kind: "boolean", code: node.kind === ts.SyntaxKind.TrueKeyword ? "true" : "false" };
    if (node.kind === ts.SyntaxKind.NullKeyword) return { kind: "empty", code: '""' };
    if (ts.isIdentifier(node)) {
      const prop = scope.get(node.text);
      if (!prop) fail(node, `Unknown prop ${node.text}; arbitrary JavaScript and globals are unsupported`);
      return prop!;
    }
    if (ts.isTemplateExpression(node)) return { kind: "text", code: join([literal(node.head.text), ...node.templateSpans.flatMap(s => [asText(value(s.expression), s.expression), literal(s.literal.text)])]) };
    if (ts.isConditionalExpression(node)) {
      const cond = value(node.condition), yes = value(node.whenTrue), no = value(node.whenFalse);
      if (cond.kind !== "boolean") fail(node.condition, "Conditions must be boolean");
      if (yes.kind === no.kind) return { kind: yes.kind, code: choice(cond.code, yes.code, no.code) };
      return { kind: "html", code: choice(cond.code, render(yes, node.whenTrue), render(no, node.whenFalse)) };
    }
    if (ts.isBinaryExpression(node)) {
      const left = value(node.left), right = value(node.right), op = node.operatorToken.kind;
      if (op === ts.SyntaxKind.AmpersandAmpersandToken) {
        if (left.kind !== "boolean") fail(node.left, "The left side of && must be boolean");
        return { kind: "html", code: choice(left.code, render(right, node.right), literal("")) };
      }
      const operators = new Map([[ts.SyntaxKind.EqualsEqualsEqualsToken, "=="], [ts.SyntaxKind.ExclamationEqualsEqualsToken, "!="],
        [ts.SyntaxKind.LessThanToken, "<"], [ts.SyntaxKind.LessThanEqualsToken, "<="], [ts.SyntaxKind.GreaterThanToken, ">"], [ts.SyntaxKind.GreaterThanEqualsToken, ">="]]);
      if (!operators.has(op) || left.kind !== "number" || right.kind !== "number") fail(node, "Only integer comparisons and boolean && are supported binary operators");
      return { kind: "boolean", code: `(${left.code} ${operators.get(op)} ${right.code})` };
    }
    if (ts.isJsxElement(node) || ts.isJsxSelfClosingElement(node)) {
      const opening = ts.isJsxElement(node) ? node.openingElement : node;
      const name = identifier(opening.tagName);
      if (opening.typeArguments) fail(opening, "JSX type arguments are unsupported");
      const attrs = new Map<string, Value>();
      for (const attr of opening.attributes.properties) {
        if (!ts.isJsxAttribute(attr)) fail(attr, "Spread attributes are unsupported");
        const a = attr as ts.JsxAttribute, key = a.name.getText(file);
        if (attrs.has(key)) fail(a, `Duplicate prop ${key}`);
        const v = !a.initializer ? { kind: "boolean" as Kind, code: "true" } : ts.isStringLiteral(a.initializer) ?
          { kind: "text" as Kind, code: literal(decode(a.initializer.text.replace(/\r\n|\r/g, "\n").replace(/\n[ \t]*/g, " "), a)) } : value(a.initializer);
        attrs.set(key, v);
      }
      const childNodes = ts.isJsxElement(node) ? node.children : undefined;
      const body = childNodes ? children(childNodes) : '""';
      if (components.has(name)) {
        edges.get(current)!.add(name);
        if (attrs.has("children")) fail(node, "Pass children between component tags");
        const props = components.get(name)!.props;
        if (props.some(p => p.name === "children")) attrs.set("children", { kind: "html", code: body });
        else if (childNodes?.some(n => !ts.isJsxText(n) || text(n).trim())) fail(node, `${name} does not accept children`);
        if ([...attrs.keys()].some(k => !props.some(p => p.name === k))) fail(node, `Unknown prop on ${name}`);
        const args = props.map(p => {
          const v = attrs.get(p.name);
          if (!v) return fail(node, `Missing required prop ${name}.${p.name}`);
          if (v.kind !== p.kind) return fail(node, `Prop ${name}.${p.name} expects ${p.kind}, received ${v.kind}`);
          return v.code;
        });
        if (expansion.includes(name)) fail(node, "Recursive component cycles are unsupported");
        // Bounded expansion removes intermediate child HTML buffers while
        // retaining separately emitted functions as a fallback for deep trees.
        if (optimize && expansion.length < 16 && expansionBudget++ < 512) {
          const saved = scope;
          scope = new Map(props.map(p => [p.name, attrs.get(p.name)!]));
          expansion.push(name);
          try {
            const body = components.get(name)!.body;
            return { kind: "html", code: render(value(body), body) };
          } finally { expansion.pop(); scope = saved; }
        }
        return { kind: "html", code: `jsx_${name}(${args.join(", ")})` };
      }
      if (!tags.has(name)) fail(node, `Unsupported HTML tag or unknown component ${name}`);
      const parts = [literal(`<${name}`)];
      for (const [key, v] of attrs) {
        if (!["id", "className", "title", "lang", "role"].includes(key) && !/^(?:data|aria)-[a-z][a-z0-9-]*$/.test(key)) fail(node, `Unsupported HTML attribute ${key}; events, styles, and raw HTML are not supported`);
        parts.push(literal(` ${key === "className" ? "class" : key}="`), escaped(asText(v, node)), literal('"'));
      }
      if (voidTags.has(name)) {
        if (childNodes?.length) fail(node, "Void HTML tags cannot have children");
        parts.push(literal("/>"));
      } else parts.push(literal(">"), body, literal(`</${name}>`));
      return { kind: "html", code: join(parts) };
    }
    return fail(node, `Unsupported ${ts.SyntaxKind[node.kind]}; this is a JSX subset, not a JavaScript runtime`);
  };
  const output: string[] = ["; Generated by examples/jsx-ssr/compile.ts. Do not edit."];
  for (const [name, component] of components) {
    current = name;
    edges.set(name, new Set());
    scope = new Map(component.props.map(p => [p.name, { kind: p.kind, code: `p_${p.name}` }]));
    expansion.push(name);
    expansionBudget = 0;
    const params = component.props.map((p, i) => `p_${p.name} : ${p.kind === "text" || p.kind === "html" ? `Arr u8 n${i}` : p.kind === "number" ? "i64{p_" + p.name + " >= 0}" : "bool"}`);
    output.push(`fn jsx_${name} (${params.join(", ")}) -> Arr u8 _\n  = ${finish(render(value(component.body), component.body))}\n`);
    expansion.pop();
  }
  const visited = new Set<string>(), active = new Set<string>();
  const visit = (name: string) => {
    if (active.has(name)) fail(components.get(name)!.node, "Recursive component cycles are unsupported");
    if (visited.has(name)) return;
    active.add(name);
    for (const child of edges.get(name)!) visit(child);
    active.delete(name); visited.add(name);
  };
  for (const name of components.keys()) visit(name);
  return output.join("\n");
}
