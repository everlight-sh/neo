# runpy2.sh : the bench/run.py compute workloads (Vif after vs before, Go for reference), both CPUs, default workers
R=/root/results; cd /root
{ go version
  echo "## mandel 3000 3000 2000"; python3 ab.py 7 0-1 2 after=bin/vif-mandel\ 3000\ 3000\ 2000 before=bin-before/vif-mandel\ 3000\ 3000\ 2000 go=./go-mandel\ 3000\ 3000\ 2000
  echo "## stencil 50000000 20"; python3 ab.py 7 0-1 2 after=bin/vif-stencil\ 50000000\ 20 before=bin-before/vif-stencil\ 50000000\ 20 go=./go-stencil\ 50000000\ 20
  echo "## stencil_small 1000000 2000"; python3 ab.py 7 0-1 2 after=bin/vif-stencil\ 1000000\ 2000 before=bin-before/vif-stencil\ 1000000\ 2000 go=./go-stencil\ 1000000\ 2000
  echo "## nbody 16384 10"; python3 ab.py 5 0-1 2 after=bin/vif-nbody\ 16384\ 10 before=bin-before/vif-nbody\ 16384\ 10 go=./go-nbody\ 16384\ 10
} > $R/runpy.txt 2>&1
cat $R/runpy.txt
