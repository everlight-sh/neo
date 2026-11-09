"""Bound heuristic inlining by emitted IR, after generic ownership lowering."""
import re

CALL = re.compile(r'\bcall [^@\n]*@([^\s(]+)\(')


def bounded_calls(bodies, policy, required=(), expansion_limit=8192, caller_limits=None):
    """Bound forced expansion at the caller, without changing other callers.

    Removing a callee's alwaysinline attribute globally lets one large cold
    function disable small helpers in unrelated hot loops. Call-site noinline
    keeps that edge out of the forced expansion while preserving the helper's
    policy everywhere else. Explicit inline requests remain mandatory.
    """
    if not expansion_limit:
        return dict(bodies)
    required, policy = set(required), set(policy)
    caller_limits = caller_limits or {}
    lines = {name: body.count('\n') + 1 for name, body in bodies.items()}
    calls = {name: [match[1] for line in body.splitlines()
                    if not re.search(r'\bnoinline\b', line)
                    for match in CALL.finditer(line)] for name, body in bodies.items()}
    sizes, active, blocked = {}, set(), {}

    def expanded(name):
        if name in sizes:
            return sizes[name]
        if name in active:
            return lines[name]
        active.add(name)
        parts = {}
        for callee in calls[name]:
            if callee in policy and callee in bodies:
                parts[callee] = parts.get(callee, 0) + expanded(callee)
        total = lines[name] + sum(parts.values())
        limit = caller_limits.get(name, expansion_limit)
        for callee, size in sorted(parts.items(), key=lambda item: (-item[1], item[0])):
            if total <= limit:
                break
            if callee not in required:
                blocked.setdefault(name, set()).add(callee)
                total -= size
        active.remove(name)
        sizes[name] = total
        return total

    for name in sorted(bodies):
        expanded(name)

    def constrain(name, body):
        if name not in blocked:
            return body
        output = []
        for line in body.splitlines():
            match = CALL.search(line)
            if match and match[1] in blocked[name] and not re.search(r'\bnoinline\b', line):
                # Call attributes precede optional instruction metadata.
                metadata = re.search(r',\s*![a-zA-Z_]', line)
                at = metadata.start() if metadata else len(line)
                line = line[:at] + ' noinline' + line[at:]
            output.append(line)
        return '\n'.join(output)

    return {name: constrain(name, body) for name, body in bodies.items()}


def bounded_policy(bodies, policy, required=(), expansion_limit=8192, body_limit=2048):
    """Keep explicit inline requests, but bound reusable-library heuristics.

    Source node counts miss the copy/drop loops generated for nested managed
    types. Count their lowered bodies, including repeated forced calls, before
    LLVM duplicates them. Ordinary calls still use LLVM's own cost model.
    """
    required = set(required)
    lines = {name: body.count('\n') + 1 for name, body in bodies.items()}
    chosen = {name for name in policy if name in required or lines.get(name, body_limit + 1) <= body_limit}
    if not expansion_limit:
        return chosen
    calls = {name: CALL.findall(body) for name, body in bodies.items()}
    sizes, active = {}, set()

    def expanded(name):
        if name in sizes:
            return sizes[name]
        if name in active:
            return lines[name]
        active.add(name)
        parts = {}
        for callee in calls[name]:
            if callee in chosen and callee in bodies:
                parts[callee] = parts.get(callee, 0) + expanded(callee)
        total = lines[name] + sum(parts.values())
        for callee, size in sorted(parts.items(), key=lambda item: (-item[1], item[0])):
            if total <= expansion_limit:
                break
            if callee not in required and callee in chosen:
                chosen.remove(callee)
                total -= size
        active.remove(name)
        sizes[name] = total
        return total

    for name in sorted(bodies):
        expanded(name)
    return chosen
