#!/bin/bash
# The whole round on one box, in order; each step's log is /root/<step>.log.
rm -f /root/fetch_new /root/fetch_main
bash /root/fetch.sh > /root/fetch.log 2>&1; tail -4 /root/fetch.log
ROUNDS=7 bash /root/ab.sh /1m 1048576 100 > /root/ab-1m.log 2>&1; tail -2 /root/ab-1m.log
ROUNDS=5 bash /root/ab.sh /64k 65536 400 > /root/ab-64k.log 2>&1; tail -1 /root/ab-64k.log
bash /root/prof.sh > /root/prof.log 2>&1; tail -1 /root/prof.log
bash /root/oneshot.sh > /root/oneshot.log 2>&1; tail -3 /root/oneshot.log
bash /root/meta.sh /root/meta.txt
bash /root/ci.sh > /root/ci.log 2>&1; tail -30 /root/ci.log
echo ALL-DONE
