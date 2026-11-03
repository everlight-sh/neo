// Prototype: Neo-like 3-point stencil, 1 thread. mode bits: 1=NT stores, 2=MADV_POPULATE_WRITE, 4=MADV_HUGEPAGE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <sys/mman.h>
#include <emmintrin.h>
#include <time.h>
#ifndef MADV_POPULATE_WRITE
#define MADV_POPULATE_WRITE 23
#endif
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec*1e3+t.tv_nsec/1e6;}
static int64_t *alloc(size_t n,int mode){
  size_t bytes=n*8; void*p=mmap(0,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
  if(mode&4) madvise(p,bytes,MADV_HUGEPAGE);
  if(mode&2){ if(madvise(p,bytes,MADV_POPULATE_WRITE)) perror("populate"); }
  return p;
}
static inline int64_t f(int64_t a,int64_t b,int64_t c){int32_t x=(int32_t)(a+2*b+c);int32_t ax=x<0?-x:x; if((uint32_t)ax>=2000006u)ax-=2000006; if((uint32_t)ax>=1000003u)ax-=1000003; return x<0?-ax:ax;}
static void pass(const int64_t*restrict xs,int64_t*restrict out,int64_t n,int nt){
  out[0]=xs[0]; out[n-1]=xs[n-1];
  int64_t i=1;
  if(!nt){ for(;i<n-1;i++) out[i]=f(xs[i-1],xs[i],xs[i+1]); return; }
  for(;i<n-1 && ((uintptr_t)(out+i)&15);i++) out[i]=f(xs[i-1],xs[i],xs[i+1]);
  for(;i+2<=n-1;i+=2){ int64_t a=f(xs[i-1],xs[i],xs[i+1]), b=f(xs[i],xs[i+1],xs[i+2]);
    _mm_stream_si128((__m128i*)(out+i),_mm_set_epi64x(b,a)); }
  for(;i<n-1;i++) out[i]=f(xs[i-1],xs[i],xs[i+1]);
  _mm_sfence();
}
int main(int argc,char**argv){
  int64_t n=atoll(argv[1]),iters=atoll(argv[2]); int mode=atoi(argv[3]);
  double t0=now();
  int64_t*a=alloc(n,mode),*b=alloc(n,mode);
  double t1=now();
  for(int64_t i=0;i<n;i++) a[i]=(i*2654435761LL)%1000003;
  double t2=now();
  for(int64_t k=0;k<iters;k++){pass(a,b,n,mode&1); int64_t*t=a;a=b;b=t;}
  double t3=now();
  int64_t s=0; for(int64_t i=0;i<n;i++) s+=a[i];
  double t4=now();
  printf("%lld\n",(long long)s);
  fprintf(stderr,"alloc %.1f fill %.1f passes %.1f sum %.1f\n",t1-t0,t2-t1,t3-t2,t4-t3);
}
