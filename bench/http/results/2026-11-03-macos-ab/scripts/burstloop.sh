#!/bin/zsh
# usage: burstloop.sh ROUNDS NAME=BIN[:ENV=V] ...  — one server per spec, interleaved bursts of 512
S=${0:h}; R=$1; shift; ulimit -n 8192; port=19300
for spec in "$@"; do
  name=${spec%%=*}; rest=${spec#*=}; bin=${rest%%:*}; envs=""; [[ $rest == *:* ]] && envs=${rest#*:}
  port=$((port+1)); env ${=envs//,/ } ${=QOS} $bin $port > $S/bl-$name.log 2>&1 & echo $! > $S/bl-$name.pid; echo "$name $port" >> $S/bl-ports
done
sleep 1
for r in $(seq 1 $R); do
  p=19300
  for spec in "$@"; do p=$((p+1)); name=${spec%%=*}; echo "r$r $name $(python3 $S/burst.py $p 512) load $(sysctl -n vm.loadavg | cut -d' ' -f2)"; sleep 0.3; done
done
for spec in "$@"; do name=${spec%%=*}; pkill -P $(cat $S/bl-$name.pid) 2>/dev/null; kill $(cat $S/bl-$name.pid) 2>/dev/null; done
rm -f $S/bl-ports
