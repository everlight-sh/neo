export PATH=/root/.bun/bin:/usr/local/go/bin:$PATH; rm -rf /root/devtest && cp -r /root/dev /root/devtest && cd /root/devtest && (cd examples/jsx-ssr && bun install --frozen-lockfile) && time ./neo test

