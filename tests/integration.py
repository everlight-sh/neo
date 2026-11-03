#!/usr/bin/env python3
"""Complete native integration entry point used by `neo test`."""
import subprocess
import sys
import os
import platform
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    subprocess.run([sys.executable,str(ROOT/'tests/heap_headers.py')],cwd=ROOT,check=True)
    subprocess.run([sys.executable,str(ROOT/'tests/observer_lifetimes.py')],cwd=ROOT,check=True)
    scripts=['index_lifetimes.py','loop_record_fields.py','data_sync.py','elf_runtime_layout.py','byte_reads.py','json_tokens.py','json_token_growth.py','native_sections.py','bitset_growth.py','bitset.py','json_views.py','json_writer.py','json_writer_growth.py','json_object_encoder.py','json_field_decoder.py','set_only_loops.py','write_only_loops.py','unique_flags.py','opcode_vm.py','deep_dispatch.py','byte_equal.py','hashmap_entry.py','utf8_ranges.py','vector_sort_cases.py','bit_counts.py','json_scan_words.py','json_scan_utf8.py','write_parts.py','byte_writes.py','shared_arrays.py','borrow_parameters.py','branch_ownership.py','json_serialization.py','reactor_language.py','push_boundaries.py','json_key_words.py','word_bytes.py','int_parse_vectors.py','map_optimizations.py','agent_readiness.py','bytesmap_smoke.py','nbody_worker_smoke.py','language_smoke.py','language_perf_checks.py','network_language.py','crypto_language.py','aes_language.py','p256_language.py','p256_protocols.py','tls_language.py','tooling_smoke.py','usability_smoke.py','json_accessors.py','compiler_confidence.py','compute_smoke.py','kernel_runtime_smoke.py','http_smoke.py','bounded_stencil_smoke.py','vector_arrays_smoke.py','bitwise_smoke.py']
    for script in scripts:
        print('\nRUN '+script,flush=True)
        subprocess.run([sys.executable,str(ROOT/'tests'/script)],cwd=ROOT,check=True)
    subprocess.run(['bun','test','examples/jsx-ssr/compile.test.ts'],cwd=ROOT,check=True)
    target=os.environ.get('NEO_TARGET') or platform.system().lower()+'-'+platform.machine()
    binary=ROOT/'.kernel-build/usability'/('ssr-'+target)
    subprocess.run(['bun','run','examples/jsx-ssr/build.ts',str(binary)],cwd=ROOT,check=True)
    subprocess.run([sys.executable,'tests/jsx_ssr_smoke.py','--binary',str(binary)],cwd=ROOT,check=True)

if __name__=='__main__':main()
