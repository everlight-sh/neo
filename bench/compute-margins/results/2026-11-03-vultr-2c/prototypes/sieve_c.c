// Prototype sieve, 1 thread. mode bits: 1=unroll4, 2=prefetchw when step>=PFMIN, 4=populate, 8=hugepage
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <sys/mman.h>
#include <time.h>
#ifndef MADV_POPULATE_WRITE
#define MADV_POPULATE_WRITE 23
#endif
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec*1e3+t.tv_nsec/1e6;}
int main(int argc,char**argv){
  int64_t n=atoll(argv[1]); int mode=atoi(argv[2]); int64_t D=argc>3?atoll(argv[3]):16; int64_t PFMIN=argc>4?atoll(argv[4]):64;
  double t0=now();
  size_t bytes=n+1; uint8_t*m=mmap(0,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
  if(mode&8) madvise(m,bytes,MADV_HUGEPAGE);
  if(mode&4) madvise(m,bytes,MADV_POPULATE_WRITE);
  double t1=now();
  for(int64_t k=0;k<=n;k++) m[k]=k>=2;
  double t2=now();
  for(int64_t i=2;i<=n&&i*i<=n;i++){
    if(!m[i]) continue;
    int64_t j=i*i, s=i;
    if((mode&2) && s>=PFMIN){
      int64_t ds=D*s;
      for(;j+ds<=n;j+=s){ __builtin_prefetch(m+j+ds,1,3); m[j]=0; }
      for(;j<=n;j+=s) m[j]=0;
    } else if(mode&1){
      int64_t s2=2*s,s3=3*s,s4=4*s;
      for(;j+s3<=n;j+=s4){ m[j]=0; m[j+s]=0; m[j+s2]=0; m[j+s3]=0; }
      for(;j<=n;j+=s) m[j]=0;
    } else {
      for(;j<=n;j+=s) m[j]=0;
    }
  }
  double t3=now();
  int64_t c=0; for(int64_t k=0;k<=n;k++) c+=m[k];
  double t4=now();
  printf("%lld\n",(long long)c);
  fprintf(stderr,"alloc %.1f fill %.1f mark %.1f count %.1f\n",t1-t0,t2-t1,t3-t2,t4-t3);
}
