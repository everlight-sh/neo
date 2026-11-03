export PATH=/root/.bun/bin:$PATH; mkdir -p /root/results; cd /root/main && python3 bench/core/compute_compare.py /root/results/baseline-main.json 9 --variant "Neo main=/root/bin-main" --rust /root/comp/rust --go /root/comp/go --bun

