// Can MADV_COLLAPSE back a fresh anonymous mapping with huge pages when THP is
// "never"? Times first-touch fill of a 400 MB block three ways and reports the
// resulting AnonHugePages for the mapping.
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <errno.h>
#include <stdint.h>
#ifndef MADV_COLLAPSE
#define MADV_COLLAPSE 25
#endif
#ifndef MADV_POPULATE_WRITE
#define MADV_POPULATE_WRITE 23
#endif
static double now(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec * 1e3 + t.tv_nsec / 1e6; }
static long huge_kb(void) {
  FILE *f = fopen("/proc/self/smaps_rollup", "r"); char line[256]; long kb = -1;
  while (fgets(line, sizeof line, f)) if (sscanf(line, "AnonHugePages: %ld kB", &kb) == 1) break;
  fclose(f); return kb;
}
int main(int argc, char **argv) {
  int mode = atoi(argv[1]); size_t bytes = (size_t)atol(argv[2]) << 20;
  char *raw = mmap(NULL, bytes + (2 << 20), PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  char *p = (char *)(((uintptr_t)raw + (2 << 20) - 1) & ~(uintptr_t)((2 << 20) - 1));
  double t0 = now(), t1 = t0; int rc = 0, err = 0;
  if (mode == 1) { rc = madvise(p, bytes, MADV_POPULATE_WRITE); err = errno; }
  if (mode == 2) {  // one fault per 2 MiB creates the page tables, then collapse
    for (size_t o = 0; o < bytes; o += 2 << 20) p[o] = 0;
    rc = madvise(p, bytes, MADV_COLLAPSE); err = errno;
  }
  if (mode == 3) { rc = madvise(p, bytes, MADV_COLLAPSE); err = errno; }  // untouched range
  if (mode == 4) { madvise(p, bytes, MADV_HUGEPAGE); for (size_t o = 0; o < bytes; o += 2 << 20) p[o] = 0; rc = madvise(p, bytes, MADV_COLLAPSE); err = errno; }
  t1 = now();
  memset(p, 1, bytes);
  double t2 = now();
  // strided pass like a sieve's large primes: one byte per 4099 bytes, 20 times
  long s = 0;
  for (int r = 0; r < 20; r++) for (size_t o = r; o < bytes; o += 4099) s += p[o];
  double t3 = now();
  printf("mode=%d rc=%d errno=%d prep=%.1fms fill=%.1fms strided=%.1fms huge=%ldkB s=%ld\n", mode, rc, rc ? err : 0, t1 - t0, t2 - t1, t3 - t2, huge_kb(), s);
  return 0;
}
