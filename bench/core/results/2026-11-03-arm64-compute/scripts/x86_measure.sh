# x86_measure.sh : main vs final vs width variants, every case of the x86 report, 1 and 2 workers, 7 rounds
export PATH=/root/.bun/bin:/usr/local/go/bin:$PATH
cd /root/final && python3 bench/core/compute_compare.py /root/results/x86-compute.json 7 --variant final=/root/bin-final --variant main=/root/bin-main --variant w2=/root/bin-w2 --variant k4w2=/root/bin-k4w2 --variant aw2=/root/bin-aw2 --rust /root/comp/rust --go /root/comp/go --cases all --workers 1,2
