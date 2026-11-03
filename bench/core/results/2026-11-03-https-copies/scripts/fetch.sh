#!/bin/bash
# bench/fetch/run.py on main (3 rounds), then on the new tree (5 rounds), HTTP and HTTPS.
export PATH=/root/.cargo/bin:/usr/local/go/bin:/root/.bun/bin:$PATH
cd /root/main && python3 bench/fetch/run.py --rounds 3 > /root/fetch-main.log 2>&1; echo "main exit=$?"
cd /root/new && python3 bench/fetch/run.py --rounds 5 > /root/fetch-new.log 2>&1; echo "new exit=$?"
ls -d /root/main/bench/fetch/results/*/ /root/new/bench/fetch/results/*/
echo FETCH-DONE
