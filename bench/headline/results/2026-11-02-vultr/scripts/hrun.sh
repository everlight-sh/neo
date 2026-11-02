# hrun.sh : the five headline rows (cli: JSON + N-body; http: hello, pipelined, memory)
O=/root/out; mkdir -p $O; cd /root/axon
bash /root/hmeta.sh $O/meta.txt
SIB=$(cat /sys/devices/system/cpu/cpu0/topology/thread_siblings_list)
CLIENT=$(python3 -c "
def parse(s): return {int(x) for part in s.split(',') for x in range(int(part.split('-')[0]), int(part.split('-')[-1]) + 1)}
print(','.join(map(str, sorted(parse(open('/sys/devices/system/cpu/online').read().strip()) - parse('$SIB')))))")
export SERVER_CPUS=0 CLIENT_CPUS=$CLIENT WRK_THREADS=2
echo "CPU 0 siblings: $SIB (sibling left idle); client and driver CPUs: $CLIENT; wrk -t2 -c64" | tee $O/setup.txt
echo "load before: $(cat /proc/loadavg)" >> $O/setup.txt
date; python3 bench/headline/run_headline.py cli $O/cli.json 15 > $O/cli.log 2>&1; echo "cli exit $?"; cat $O/cli.log
date; python3 bench/headline/run_headline.py http $O/http.json 11 > $O/http.log 2>&1; echo "http exit $?"; cat $O/http.log
date; echo "load after: $(cat /proc/loadavg)" >> $O/setup.txt
cp /root/build-*.log $O/ 2>/dev/null; echo ALL-DONE
