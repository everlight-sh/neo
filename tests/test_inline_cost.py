import unittest
from types import SimpleNamespace
from neoc.inline_cost import bounded_policy, bounded_calls
from neoc import native_libraries, syntax as S


def body(name, lines=1, calls=()):
    return '\n'.join(['define void @'+name+'() {', *('call void @'+callee+'()' for callee in calls), *(['; cost'] * lines), 'ret void', '}'])


class InlineCost(unittest.TestCase):
    def test_large_generic_lowering_keeps_an_ordinary_call(self):
        bodies = {'small': body('small'), 'large': body('large', 2100)}
        self.assertEqual(bounded_policy(bodies, set(bodies)), {'small'})

    def test_repeated_transitive_calls_count_toward_expansion(self):
        bodies = {'leaf': body('leaf', 100), 'middle': body('middle', calls=['leaf'] * 4),
                  'root': body('root', calls=['middle'] * 4)}
        chosen = bounded_policy(bodies, {'leaf', 'middle'}, expansion_limit=1000)
        self.assertIn('leaf', chosen)
        self.assertNotIn('middle', chosen)

    def test_explicit_inline_survives_both_limits(self):
        bodies = {'large': body('large', 2100), 'root': body('root', calls=['large'] * 4)}
        self.assertIn('large', bounded_policy(bodies, {'large'}, required={'large'}, expansion_limit=100))

    def test_zero_expansion_limit_and_recursive_ir_terminate(self):
        bodies = {'a': body('a', calls=['b']), 'b': body('b', calls=['a'])}
        self.assertEqual(bounded_policy(bodies, set(bodies), expansion_limit=0), set(bodies))
        self.assertEqual(bounded_policy(bodies, set(bodies)), set(bodies))

    def test_policy_is_independent_of_dictionary_order(self):
        bodies = {'leaf': body('leaf', 100), 'middle': body('middle', calls=['leaf'] * 4),
                  'root': body('root', calls=['middle'] * 4)}
        self.assertEqual(bounded_policy(bodies, {'leaf', 'middle'}, expansion_limit=1000),
                         bounded_policy(dict(reversed(list(bodies.items()))), {'leaf', 'middle'}, expansion_limit=1000))

    def test_library_policy_measures_lowered_generics_and_keeps_explicit_inline(self):
        program = S.parse('fn small()->i64=1 fn generic()->i64=1 inline fn explicit()->i64=1')
        gen = SimpleNamespace(fns=program.fns, fn_map={f.name: f for f in program.fns},
                              library_names={f.name for f in program.fns}, policy_inline_enabled=True,
                              inline_budget=160, inline_expansion=262144,
                              is_recursive=lambda f: False, node_count=lambda f: 1,
                              fname=lambda f, mode: '@'+f.name+'__'+mode)
        bodies = {f.name+'__'+mode: body(f.name+'__'+mode, 2100 if f.name != 'small' else 1)
                  for f in program.fns for mode in ('par', 'seq')}
        chosen = native_libraries.inline_policy(gen, program.fns, bodies)
        self.assertEqual(chosen, {'small__par', 'small__seq', 'explicit__par', 'explicit__seq'})

    def test_large_caller_cannot_disable_another_callers_inline_policy(self):
        bodies={'leaf':body('leaf',100),'fast':body('fast',calls=['leaf']),
                'cold':body('cold',calls=['leaf']*100)}
        bounded=bounded_calls(bodies,{'leaf'},expansion_limit=1000)
        self.assertNotIn('noinline',bounded['fast'])
        self.assertEqual(bounded['cold'].count('noinline'),100)
        self.assertEqual(bounded['leaf'],bodies['leaf'])
        self.assertEqual(bounded_calls({'leaf':bodies['leaf'],'fast':bodies['fast']},{'leaf'},expansion_limit=1000)['fast'],bounded['fast'])
        self.assertEqual(bounded_calls(dict(reversed(list(bodies.items()))),{'leaf'},expansion_limit=1000),bounded)

    def test_call_budget_preserves_explicit_requests_and_instruction_metadata(self):
        bodies={'leaf':body('leaf',100),'root':body('root',calls=['leaf']*20)}
        self.assertNotIn('noinline',bounded_calls(bodies,{'leaf'},{'leaf'},1000)['root'])
        bodies['root']=bodies['root'].replace('call void @leaf()','call void @leaf(), !llvm.access.group !0')
        self.assertIn('@leaf() noinline, !llvm.access.group !0',bounded_calls(bodies,{'leaf'},expansion_limit=1000)['root'])

    def test_llvm_preserves_the_bounded_call_and_inlines_the_other_caller(self):
        import shutil,subprocess,tempfile,re
        from pathlib import Path
        if not shutil.which('clang'):self.skipTest('clang is required for the backend check')
        bodies={'leaf':'define internal i64 @leaf(i64 %x) alwaysinline {\n%v = mul i64 %x, 7\nret i64 %v\n}',
                'fast':'define i64 @fast(i64 %x) {\n%v = call i64 @leaf(i64 %x)\nret i64 %v\n}',
                'bounded':'define i64 @bounded(i64 %x) {\n%v = call i64 @leaf(i64 %x)\nret i64 %v\n}'}
        # Make just one caller exceed the budget; the LLVM input remains valid.
        bodies['bounded']=bodies['bounded'].replace('%v =',('\n'*30)+'%v =')
        bounded=bounded_calls(bodies,{'leaf'},expansion_limit=20)
        with tempfile.TemporaryDirectory(prefix='neo-inline-edge-') as temporary:
            root=Path(temporary);source=root/'input.ll';output=root/'optimized.ll';source.write_text('\n'.join(bounded.values()))
            subprocess.run(['clang','-Wno-override-module','-O3','-S','-emit-llvm',str(source),'-o',str(output)],check=True,capture_output=True)
            optimized=output.read_text()
        fast=re.search(r'define[^\n]*@fast\([^\n]*\{(.*?)^}',optimized,re.S|re.M)[1]
        constrained=re.search(r'define[^\n]*@bounded\([^\n]*\{(.*?)^}',optimized,re.S|re.M)[1]
        self.assertNotIn('@leaf(',fast)
        self.assertIn('@leaf(',constrained)

    def test_cached_hint_uses_a_call_budget_without_disabling_the_helper(self):
        import tempfile
        from pathlib import Path
        program = S.parse('fn leaf()->i64=1 fn main()->i64=leaf()')
        leaf = body('leaf__seq', 100).replace('() {', '() alwaysinline {')
        application = body('main', calls=['leaf__seq'] * 100)
        gen = SimpleNamespace(fns=program.fns, fn_map={f.name: f for f in program.fns},
                              library_names={'leaf'}, policy_inline_enabled=True,
                              inline_budget=160, inline_expansion=1000,
                              is_recursive=lambda f: False, node_count=lambda f: 1,
                              fname=lambda f, mode: '@'+f.name+'__'+mode,
                              funcs=[application], module_header='')
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'hints.ll').write_text(leaf+'\n')
            merged, _, _ = native_libraries.merge(gen, folder, 'fixture', {'functions':['leaf__seq'], 'object_sha256':'fixture'})
        self.assertIn('define available_externally hidden void @leaf__seq() alwaysinline', merged)
        self.assertEqual(merged.count('call void @leaf__seq() noinline'),100)

    def test_object_budget_does_not_leak_into_application_hints(self):
        gen=SimpleNamespace(fns=[],inline_expansion=262144)
        bodies={'leaf':body('leaf',100),'root':body('root',calls=['leaf']*400)}
        self.assertEqual(native_libraries.bound_calls(gen,bodies,{'leaf'},library=True)['root'].count('noinline'),400)
        self.assertNotIn('noinline',native_libraries.bound_calls(gen,bodies,{'leaf'})['root'])

    def test_object_budget_preserves_pure_expansion_and_bounds_io(self):
        program = S.parse('fn pure()->i64=1 effect fn io()->i64=1')
        gen = SimpleNamespace(fns=program.fns, inline_expansion=262144,
                              fname=lambda fn, mode: '@'+fn.name+'__'+mode)
        bodies = {'leaf': body('leaf', 100),
                  'pure__seq': body('pure__seq', calls=['leaf']*100),
                  'io__seq': body('io__seq', calls=['leaf']*100)}
        bounded = native_libraries.bound_calls(gen,bodies,{'leaf'},library=True)
        self.assertNotIn('noinline',bounded['pure__seq'])
        self.assertEqual(bounded['io__seq'].count('noinline'),100)


if __name__ == '__main__':
    unittest.main()
