#include <stdio.h>
#include <time.h>
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec*1e-9;}
#define N 50000000L
#define R8(x) x x x x x x x x
int main(void){
  double t0,t1; long x=0;
  t0=now(); for(long i=0;i<N;i++){__asm__ volatile(R8("add %0,%0,#1\n"):"+r"(x));} t1=now();
  double c=(t1-t0)/(8.0*N); printf("GHz %.3f\n",1e-9/c);
#define T(name,ins) t0=now(); for(long i=0;i<N;i++){__asm__ volatile( \
  "fmov v8.2d, #1.25\n fmov v9.2d, #1.75\n" R8(ins "\n") ::: "v0","v1","v2","v3","v4","v5","v6","v7","v8","v9");} t1=now(); \
  printf("%-22s %.2f cycles/instr\n",name,(t1-t0)/c/(8.0*N));
  T("fdiv v.2d", "fdiv v0.2d, v8.2d, v9.2d")
  T("fdiv d", "fdiv d0, d8, d9")
  T("fsqrt v.2d", "fsqrt v0.2d, v9.2d")
  T("fsqrt d", "fsqrt d0, d9")
  T("fdiv d + fsqrt d", "fdiv d0, d8, d9\n fsqrt d1, d9")
  T("fdiv 2d + fsqrt 2d", "fdiv v0.2d, v8.2d, v9.2d\n fsqrt v1.2d, v9.2d")
  T("fmla 2d", "fmla v0.2d, v8.2d, v9.2d\n fmla v1.2d, v8.2d, v9.2d\n fmla v2.2d, v8.2d, v9.2d\n fmla v3.2d, v8.2d, v9.2d")
  T("frecpe 2d", "frecpe v0.2d, v9.2d")
  T("frsqrte 2d", "frsqrte v0.2d, v9.2d")
  T("fmul 2d indep x8", "fmul v0.2d, v8.2d, v9.2d\n fmul v1.2d, v8.2d, v9.2d\n fmul v2.2d, v8.2d, v9.2d\n fmul v3.2d, v8.2d, v9.2d\n fmul v4.2d, v8.2d, v9.2d\n fmul v5.2d, v8.2d, v9.2d\n fmul v6.2d, v8.2d, v9.2d\n fmul v7.2d, v8.2d, v9.2d")
  T("fmla 2d indep x8", "fmla v0.2d, v8.2d, v9.2d\n fmla v1.2d, v8.2d, v9.2d\n fmla v2.2d, v8.2d, v9.2d\n fmla v3.2d, v8.2d, v9.2d\n fmla v4.2d, v8.2d, v9.2d\n fmla v5.2d, v8.2d, v9.2d\n fmla v6.2d, v8.2d, v9.2d\n fmla v7.2d, v8.2d, v9.2d")
  T("fsqrt 2d + 8 fmul", "fsqrt v0.2d, v9.2d\n fmul v1.2d, v8.2d, v9.2d\n fmul v2.2d, v8.2d, v9.2d\n fmul v3.2d, v8.2d, v9.2d\n fmul v4.2d, v8.2d, v9.2d\n fmul v5.2d, v8.2d, v9.2d\n fmul v6.2d, v8.2d, v9.2d\n fmul v7.2d, v8.2d, v9.2d\n fmul v1.2d, v8.2d, v9.2d")
  T("add x3 dep (cal)", "add x9, x9, #1\n add x9, x9, #1\n add x9, x9, #1")
  return 0;}
