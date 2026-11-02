"""Effect isolation, FFI signatures and optimiser regressions (no external deps)."""
import unittest

from neoc import syntax as S
from neoc.check import Checker, CheckError
from neoc.fold import fold_program
from neoc.graph import hash_program
from neoc.llvm import LLVMGen


def checked(source):
    program = S.parse(source)
    hash_program(program)
    checker = Checker(program)
    checker.run()
    unproven = [o for o in checker.obligations if o['status'] not in ('proven', 'checked')]
    if unproven: raise AssertionError(unproven)
    return program


class SystemsTests(unittest.TestCase):
    def test_widened_loop_array_guard_names_current_length(self):
        checked('fn main(n:i64) -> i64 = loop(i=0,a=arr(j in 0..1) j) while i<n next(i+1,if len(a)>0 then push(a,a[0]) else push(a,0)) yield len(a)')

    def test_widened_loop_array_does_not_keep_initial_length(self):
        with self.assertRaises(AssertionError):
            checked('fn main(n:i64) -> i64 = loop(i=0,a=arr(j in 0..1) j) while i<n next(i+1,let v=a[0] in arr(j in 0..0) v) yield len(a)')

    def test_widened_loop_array_guard_does_not_cover_next_index(self):
        with self.assertRaises(AssertionError):
            checked('fn main(n:i64) -> i64 = loop(i=0,a=arr(j in 0..1) j) while i<n next(i+1,if len(a)>0 then push(a,a[len(a)]) else push(a,0)) yield len(a)')

    def test_bitwise_arity_and_operand_types(self):
        for expression in ('bit_and(1)', 'bit_or(1,2,3)', 'bit_xor(1,2.0)', 'byte_swap64(1,2)', 'byte_swap64(1.0)'):
            with self.subTest(expression=expression), self.assertRaises(CheckError):
                checked('fn main()->i64='+expression)

    def test_ffi_requires_effect(self):
        with self.assertRaises(CheckError):
            checked('extern fn getpid () -> i32 fn main () -> i64 = i64(getpid())')

    def test_effect_is_transitive(self):
        with self.assertRaises(CheckError):
            checked('effect fn action () -> i64 = 7 fn main () -> i64 = action()')

    def test_foreign_call_in_effect_main(self):
        checked('extern fn getpid () -> i32 effect fn main () -> i64 = i64(getpid())')

    def test_effect_cannot_hide_in_refinement(self):
        with self.assertRaises(CheckError):
            checked('extern fn read_number () -> i64 effect fn main (n : i64{read_number() > 0}) -> i64 = n')

    def test_effect_cannot_run_in_parallel_comprehension(self):
        with self.assertRaises(CheckError):
            checked('extern fn read_number () -> i64 effect fn main () -> i64 = sum(i in 0..10) read_number()')

    def test_pointer_access_requires_effect(self):
        with self.assertRaises(CheckError):
            checked('fn main () -> i64 = load_i64(null(), 0)')

    def test_ring_atomics_are_32_bit_acquire_release(self):
        with self.assertRaises(CheckError):
            checked('fn main () -> i64 = i64(atomic_load_i32(null(), 0))')
        source = 'effect fn main () -> i64 = let p = stack_alloc(8) in let s = atomic_store_i32(p, 4, i32(7)) in i64(atomic_load_i32(p, 4))'
        program = checked(source)
        ir = LLVMGen(program.fns, hash_program(program), 'x86_64-unknown-linux-gnu').program()
        self.assertRegex(ir, r'store atomic i32 \S+, ptr \S+ release, align 4')
        self.assertRegex(ir, r'load atomic i32, ptr \S+ acquire, align 4')

    def test_syscall_requires_effect(self):
        with self.assertRaises(CheckError):
            checked('fn main () -> i64 = syscall6(20, 0, 0, 0, 0, 0, 0)')

    def test_fork_requires_effect(self):
        with self.assertRaises(CheckError):
            checked('fn main () -> i64 = fork_syscall()')

    def test_runtime_storage_requires_effect(self):
        with self.assertRaises(CheckError):
            checked('fn main () -> i64 = ptr_to_i64(runtime_state())')

    def test_handler_must_remain_pure(self):
        with self.assertRaises(CheckError):
            checked('effect fn handler (bytes : Arr u8 n) -> Arr u8 _ = bytes effect fn main () -> i64 = serve(8080, handler)')

    def test_foreign_arrays_rejected(self):
        with self.assertRaises(CheckError):
            checked('extern fn foreign (a : Arr u8 n) -> i64 fn main () -> i64 = 0')

    def test_effect_calls_are_never_folded(self):
        p = checked('effect fn action (n : i64) -> i64 = n effect fn main () -> i64 = action(42)')
        self.assertEqual(fold_program(p.fns), 0)
        self.assertIsInstance(p.fns[-1].body, S.Call)

    def test_forward_refinement_is_available(self):
        checked('fn main (n : i64) -> i64 = n / positive() fn positive () -> i64 {result > 0} = 2')

    def test_duplicate_functions_rejected(self):
        with self.assertRaises(CheckError):
            checked('fn main () -> i64 = 1 fn main () -> i64 = 2')

    def test_extern_symbol_identity_is_hashed(self):
        a = S.parse('extern fn alpha () -> i64 effect fn main () -> i64 = alpha()')
        b = S.parse('extern fn beta () -> i64 effect fn main () -> i64 = beta()')
        self.assertNotEqual(hash_program(a)['main'], hash_program(b)['main'])

    def test_main_cannot_conflict_with_process_entry(self):
        with self.assertRaises(CheckError): checked('extern fn main () -> i64')

    def test_data_requires_storage_with_a_scope(self):
        with self.assertRaises(CheckError):
            checked('effect fn main () -> i64 = let p = data(concat("a", "b")) in 0')


if __name__ == '__main__': unittest.main()
