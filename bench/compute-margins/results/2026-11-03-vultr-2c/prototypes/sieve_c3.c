// Sieve marking variants; mode: 0 plain, 1 unroll4, 4 check-before-store (all steps), 5 unroll4 small + check step>=64,
// 6 unroll4 small + check unrolled step>=64, 7 = 5 with populate. Prints split.
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <sys/mman.h>
#include <time.h>
#ifndef MADV_POPULATE_WRITE
#define MADV_POPULATE_WRITE 23
#endif
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec*1e3+t.tv_nsec/1e6;}
static void mark(uint8_t*m,int64_t n,int64_t j,int64_t s,int mode){
  if(mode==0){ for(;j<=n;j+=s) m[j]=0; return; }
  if(mode==4 || ((mode==5||mode==7) && s>=64)){ for(;j<=n;j+=s) if(m[j]) m[j]=0; return; }
  if(mode==6 && s>=64){ for(;j+3*s<=n;j+=4*s){ if(m[j])m[j]=0; if(m[j+s])m[j+s]=0; if(m[j+2*s])m[j+2*s]=0; if(m[j+3*s])m[j+3*s]=0;} for(;j<=n;j+=s) if(m[j]) m[j]=0; return; }
  for(;j+3*s<=n;j+=4*s){ m[j]=0;m[j+s]=0;m[j+2*s]=0;m[j+3*s]=0;} for(;j<=n;j+=s) m[j]=0;
}
int main(int argc,char**argv){
  int64_t n=atoll(argv[1]); int mode=atoi(argv[2]);
  double ta=now();
  size_t bytes=n+1; uint8_t*m=mmap(0,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
  if(mode==7) madvise(m,bytes,MADV_POPULATE_WRITE);
  double tf=now();
  for(int64_t k=0;k<=n;k++) m[k]=k>=2;
  double cuts[]={8,64,512,4096,1e18}; double t[5]={0}; int ci=0; double t0=now(); double tm=t0;
  for(int64_t i=2;i<=n&&i*i<=n;i++){
    while(i>=cuts[ci]){ double t1=now(); t[ci]+=t1-t0; t0=t1; ci++; }
    if(!m[i]) continue;
    mark(m,n,i*i,i,mode);
  }
  t[ci]+=now()-t0; double tc=now();
  int64_t c=0; for(int64_t k=0;k<=n;k++) c+=m[k];
  double te=now();
  printf("%lld\n",(long long)c);
  fprintf(stderr,"alloc %.1f fill %.1f | p<8 %.1f | 8-64 %.1f | 64-512 %.1f | 512-4096 %.1f | >=4096 %.1f | mark %.1f count %.1f total %.1f\n",
    tf-ta,tm-tf,t[0],t[1],t[2],t[3],t[4],tc-tm,te-tc,te-ta);
}
