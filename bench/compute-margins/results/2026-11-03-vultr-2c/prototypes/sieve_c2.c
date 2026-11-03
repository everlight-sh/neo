// Sieve marking split by prime range; mode: 0 plain, 1 unroll4, 2 unroll8, 3 unroll4+prefetch(D=16, step>=1024)
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <sys/mman.h>
#include <time.h>
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec*1e3+t.tv_nsec/1e6;}
static void mark(uint8_t*m,int64_t n,int64_t j,int64_t s,int mode){
  if(mode==0){ for(;j<=n;j+=s) m[j]=0; return; }
  if(mode==3 && s>=1024){ int64_t ds=16*s; for(;j+ds<=n;j+=s){ __builtin_prefetch(m+j+ds,1,3); m[j]=0;} for(;j<=n;j+=s) m[j]=0; return; }
  if(mode==2){ for(;j+7*s<=n;j+=8*s){ m[j]=0;m[j+s]=0;m[j+2*s]=0;m[j+3*s]=0;m[j+4*s]=0;m[j+5*s]=0;m[j+6*s]=0;m[j+7*s]=0;} for(;j<=n;j+=s) m[j]=0; return; }
  for(;j+3*s<=n;j+=4*s){ m[j]=0;m[j+s]=0;m[j+2*s]=0;m[j+3*s]=0;} for(;j<=n;j+=s) m[j]=0;
}
int main(int argc,char**argv){
  int64_t n=atoll(argv[1]); int mode=atoi(argv[2]); int hp=argc>3?atoi(argv[3]):0;
  size_t bytes=n+1; uint8_t*m=mmap(0,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
  if(hp) madvise(m,bytes,MADV_HUGEPAGE);
  for(int64_t k=0;k<=n;k++) m[k]=k>=2;
  double cuts[]={8,64,512,4096,1e18}; double t[5]={0}; int ci=0; double t0=now(); int64_t stores[5]={0};
  for(int64_t i=2;i<=n&&i*i<=n;i++){
    while(i>=cuts[ci]){ double t1=now(); t[ci]+=t1-t0; t0=t1; ci++; }
    if(!m[i]) continue;
    stores[ci]+=(n-i*i)/i+1;
    mark(m,n,i*i,i,mode);
  }
  t[ci]+=now()-t0;
  int64_t c=0; for(int64_t k=0;k<=n;k++) c+=m[k];
  printf("%lld\n",(long long)c);
  fprintf(stderr,"p<8 %.1f (%.0fM st) | 8-64 %.1f (%.0fM) | 64-512 %.1f (%.0fM) | 512-4096 %.1f (%.0fM) | >=4096 %.1f (%.0fM) | total %.1f\n",
    t[0],stores[0]/1e6,t[1],stores[1]/1e6,t[2],stores[2]/1e6,t[3],stores[3]/1e6,t[4],stores[4]/1e6,t[0]+t[1]+t[2]+t[3]+t[4]);
}
