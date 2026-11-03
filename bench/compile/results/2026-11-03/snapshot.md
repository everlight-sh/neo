# IR snapshot: parent commit 6e18e65 against this branch

114 corpus programs, each lowered to LLVM IR (`--emit-llvm`, no clang) for aarch64-unknown-linux-gnu, arm64-apple-macosx, x86_64-unknown-linux-gnu. A program counts as changed when its IR differs on any target. `examples/unproven.neo` is rejected by both trees with identical error reports. Front-end seconds were measured on a shared development Mac and are indicative only.

Unchanged on every target: 99 programs. Changed: 15.

| Program | Target | IR bytes before | IR bytes after | Front-end s before | after |
|---|---|---:|---:|---:|---:|
| bench/core/orders_stages.neo | aarch64-unknown-linux-gnu | 1,114,682 | 1,114,658 | 4.41 | 1.81 |
| bench/core/orders_stages.neo | arm64-apple-macosx | 1,113,254 | 1,113,230 | 4.25 | 1.70 |
| bench/core/orders_stages.neo | x86_64-unknown-linux-gnu | 1,133,632 | 1,133,608 | 4.63 | 2.16 |
| bench/fetch/fetch.neo | aarch64-unknown-linux-gnu | 13,677,502 | 13,677,466 | 9.98 | 4.64 |
| bench/fetch/fetch.neo | arm64-apple-macosx | 13,675,479 | 13,675,443 | 9.40 | 4.72 |
| bench/fetch/fetch.neo | x86_64-unknown-linux-gnu | 13,692,110 | 13,692,074 | 9.79 | 4.76 |
| compiler/src/main.neo | aarch64-unknown-linux-gnu | 46,805,798 | 46,805,666 | 8.87 | 4.67 |
| compiler/src/main.neo | arm64-apple-macosx | 46,805,029 | 46,804,897 | 8.63 | 4.41 |
| compiler/src/main.neo | x86_64-unknown-linux-gnu | 46,816,644 | 46,816,512 | 9.02 | 4.84 |
| tests/fixtures/agent_transport.neo | aarch64-unknown-linux-gnu | 11,212,938 | 11,212,902 | 9.69 | 4.59 |
| tests/fixtures/agent_transport.neo | arm64-apple-macosx | 11,210,920 | 11,210,884 | 9.84 | 4.84 |
| tests/fixtures/agent_transport.neo | x86_64-unknown-linux-gnu | 11,226,126 | 11,226,090 | 9.94 | 4.66 |
| tests/fixtures/http_keepalive.neo | aarch64-unknown-linux-gnu | 13,180,169 | 13,180,133 | 9.93 | 6.02 |
| tests/fixtures/http_keepalive.neo | arm64-apple-macosx | 13,178,147 | 13,178,111 | 10.12 | 5.88 |
| tests/fixtures/http_keepalive.neo | x86_64-unknown-linux-gnu | 13,193,357 | 13,193,321 | 9.93 | 5.93 |
| tests/fixtures/json_construct_probe.neo | aarch64-unknown-linux-gnu | 2,092,408 | 2,092,384 | 3.76 | 2.17 |
| tests/fixtures/json_construct_probe.neo | arm64-apple-macosx | 2,089,120 | 2,089,096 | 3.71 | 1.93 |
| tests/fixtures/json_construct_probe.neo | x86_64-unknown-linux-gnu | 2,122,989 | 2,122,965 | 3.85 | 2.54 |
| tests/fixtures/json_field_decoder.neo | aarch64-unknown-linux-gnu | 1,681,840 | 1,681,828 | 3.66 | 1.79 |
| tests/fixtures/json_field_decoder.neo | arm64-apple-macosx | 1,678,553 | 1,678,541 | 3.54 | 1.73 |
| tests/fixtures/json_field_decoder.neo | x86_64-unknown-linux-gnu | 1,708,018 | 1,708,006 | 3.33 | 1.89 |
| tests/fixtures/json_object_encoder.neo | aarch64-unknown-linux-gnu | 2,160,353 | 2,160,317 | 4.34 | 1.71 |
| tests/fixtures/json_object_encoder.neo | arm64-apple-macosx | 2,157,066 | 2,157,030 | 3.73 | 1.65 |
| tests/fixtures/json_object_encoder.neo | x86_64-unknown-linux-gnu | 2,182,227 | 2,182,191 | 4.03 | 1.67 |
| tests/fixtures/json_writer_probe.neo | aarch64-unknown-linux-gnu | 2,044,927 | 2,044,903 | 4.37 | 1.62 |
| tests/fixtures/json_writer_probe.neo | arm64-apple-macosx | 2,041,640 | 2,041,616 | 4.15 | 1.62 |
| tests/fixtures/json_writer_probe.neo | x86_64-unknown-linux-gnu | 2,068,224 | 2,068,200 | 4.44 | 1.69 |
| tests/fixtures/language_p384.neo | aarch64-unknown-linux-gnu | 2,278,742 | 2,278,730 | 3.64 | 1.44 |
| tests/fixtures/language_p384.neo | arm64-apple-macosx | 2,275,461 | 2,275,449 | 3.26 | 1.39 |
| tests/fixtures/language_p384.neo | x86_64-unknown-linux-gnu | 2,283,645 | 2,283,633 | 3.48 | 1.55 |
| tests/fixtures/language_tls.neo | aarch64-unknown-linux-gnu | 8,566,322 | 8,566,286 | 8.72 | 5.13 |
| tests/fixtures/language_tls.neo | arm64-apple-macosx | 8,564,311 | 8,564,275 | 8.74 | 4.84 |
| tests/fixtures/language_tls.neo | x86_64-unknown-linux-gnu | 8,579,510 | 8,579,474 | 8.27 | 5.17 |
| tests/fixtures/language_tls12.neo | aarch64-unknown-linux-gnu | 10,535,951 | 10,535,915 | 9.11 | 5.39 |
| tests/fixtures/language_tls12.neo | arm64-apple-macosx | 10,533,939 | 10,533,903 | 8.83 | 5.18 |
| tests/fixtures/language_tls12.neo | x86_64-unknown-linux-gnu | 10,549,139 | 10,549,103 | 8.91 | 5.05 |
| tests/fixtures/language_tls_web.neo | aarch64-unknown-linux-gnu | 10,423,555 | 10,423,519 | 8.96 | 5.17 |
| tests/fixtures/language_tls_web.neo | arm64-apple-macosx | 10,421,543 | 10,421,507 | 9.42 | 4.93 |
| tests/fixtures/language_tls_web.neo | x86_64-unknown-linux-gnu | 10,436,743 | 10,436,707 | 8.62 | 5.47 |
| tests/fixtures/language_x509.neo | aarch64-unknown-linux-gnu | 3,885,875 | 3,885,863 | 5.58 | 2.78 |
| tests/fixtures/language_x509.neo | arm64-apple-macosx | 3,882,591 | 3,882,579 | 5.69 | 2.67 |
| tests/fixtures/language_x509.neo | x86_64-unknown-linux-gnu | 3,898,710 | 3,898,698 | 5.49 | 2.85 |
| tests/fixtures/x509_web.neo | aarch64-unknown-linux-gnu | 4,972,524 | 4,972,500 | 5.49 | 2.69 |
| tests/fixtures/x509_web.neo | arm64-apple-macosx | 4,969,240 | 4,969,216 | 5.42 | 2.57 |
| tests/fixtures/x509_web.neo | x86_64-unknown-linux-gnu | 4,985,359 | 4,985,335 | 5.39 | 2.73 |

Front-end seconds over all 342 jobs: before 1561.3, after 1051.5.

Unchanged programs:

- bench/core/document_decoder.neo
- bench/core/orders_decoder.neo
- bench/core/orders_json.neo
- examples/greet.neo
- examples/hello.neo
- examples/http.neo
- examples/library_bench.neo
- examples/mandel.neo
- examples/nbody.neo
- examples/sieve.neo
- examples/ssr.neo
- examples/stencil.neo
- examples/unproven.neo
- tests/fixtures/agent_codecs.neo
- tests/fixtures/agent_libraries.neo
- tests/fixtures/agent_process.neo
- tests/fixtures/agent_runtime_bench.neo
- tests/fixtures/agent_utilities.neo
- tests/fixtures/allocator_cache.neo
- tests/fixtures/bit_counts.neo
- tests/fixtures/bitset.neo
- tests/fixtures/bitset_growth.neo
- tests/fixtures/bitwise.neo
- tests/fixtures/borrow_parameters.neo
- tests/fixtures/borrow_records.neo
- tests/fixtures/bounded_stencil.neo
- tests/fixtures/branch_ownership.neo
- tests/fixtures/byte_equal.neo
- tests/fixtures/byte_reads.neo
- tests/fixtures/byte_writes.neo
- tests/fixtures/bytesmap.neo
- tests/fixtures/callbacks.neo
- tests/fixtures/data_sync.neo
- tests/fixtures/datagram.neo
- tests/fixtures/field_moves.neo
- tests/fixtures/generic_map_bench.neo
- tests/fixtures/hashmap_entry.neo
- tests/fixtures/hashmap_entry_alloc.neo
- tests/fixtures/heap_headers.neo
- tests/fixtures/http_client.neo
- tests/fixtures/index_lifetimes.neo
- tests/fixtures/int_parse_vectors.neo
- tests/fixtures/int_text_vectors.neo
- tests/fixtures/integers.neo
- tests/fixtures/io.neo
- tests/fixtures/json_access_probe.neo
- tests/fixtures/json_key_words.neo
- tests/fixtures/json_probe.neo
- tests/fixtures/json_scan_words.neo
- tests/fixtures/json_token_growth.neo
- tests/fixtures/json_tokens.neo
- tests/fixtures/json_views.neo
- tests/fixtures/json_writer_growth.neo
- tests/fixtures/kernel_runtime.neo
- tests/fixtures/language_aes.neo
- tests/fixtures/language_bench.neo
- tests/fixtures/language_buffer.neo
- tests/fixtures/language_cancel.neo
- tests/fixtures/language_collections.neo
- tests/fixtures/language_crypto.neo
- tests/fixtures/language_dns.neo
- tests/fixtures/language_drop_once.neo
- tests/fixtures/language_fork_file.neo
- tests/fixtures/language_hash.neo
- tests/fixtures/language_http.neo
- tests/fixtures/language_kernel.neo
- tests/fixtures/language_p256.neo
- tests/fixtures/language_resources.neo
- tests/fixtures/language_sha512.neo
- tests/fixtures/language_types.neo
- tests/fixtures/language_unit.neo
- tests/fixtures/loop_record_fields.neo
- tests/fixtures/map_array_borrows.neo
- tests/fixtures/map_inline_keys.neo
- tests/fixtures/map_vectors.neo
- tests/fixtures/memory_blocks.neo
- tests/fixtures/observer_lifetimes.neo
- tests/fixtures/opcode_vm.neo
- tests/fixtures/owned_records.neo
- tests/fixtures/parallel_runtime.neo
- tests/fixtures/pure_process_child.neo
- tests/fixtures/push_boundaries.neo
- tests/fixtures/reactor.neo
- tests/fixtures/resource_arena.neo
- tests/fixtures/resource_factory.neo
- tests/fixtures/set_only_loops.neo
- tests/fixtures/shared_arrays.neo
- tests/fixtures/shared_worker_abi.neo
- tests/fixtures/socket_cancellation.neo
- tests/fixtures/stdlib.neo
- tests/fixtures/u16_units.neo
- tests/fixtures/unique_flags.neo
- tests/fixtures/utf8_ranges.neo
- tests/fixtures/vector_arrays.neo
- tests/fixtures/vector_sort_probe.neo
- tests/fixtures/word_bytes.neo
- tests/fixtures/write_only_loops.neo
- tests/fixtures/write_parts.neo
- tests/fixtures/x509_bundle.neo
