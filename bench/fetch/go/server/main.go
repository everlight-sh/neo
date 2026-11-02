// The target of the fetch benchmark: server PORT [TLSPORT CERT KEY]. Fixed
// bodies with a Content-Length at /hello (13 bytes), /64k and /1m, over HTTP
// and, given a certificate, HTTPS (TLS 1.3, HTTP/1.1 only). /conns answers how
// many connections both have accepted, so a run can show whether its client
// reused them.
package main

import (
	"bytes"
	"crypto/tls"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"strconv"
	"sync/atomic"
)

func main() {
	var conns atomic.Int64
	bodies := map[string][]byte{
		"/hello": []byte("Hello, World!"),
		"/64k":   bytes.Repeat([]byte("x"), 64<<10),
		"/1m":    bytes.Repeat([]byte("x"), 1<<20),
	}
	mux := http.NewServeMux()
	for path, body := range bodies {
		mux.HandleFunc(path, func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/octet-stream")
			w.Header().Set("Content-Length", strconv.Itoa(len(body)))
			w.Write(body)
		})
	}
	mux.HandleFunc("/conns", func(w http.ResponseWriter, r *http.Request) { fmt.Fprint(w, conns.Load()) })
	count := func(c net.Conn, state http.ConnState) {
		if state == http.StateNew {
			conns.Add(1)
		}
	}
	if len(os.Args) > 4 {
		secure := &http.Server{Addr: "127.0.0.1:" + os.Args[2], Handler: mux, ConnState: count,
			TLSConfig:    &tls.Config{MinVersion: tls.VersionTLS13},
			TLSNextProto: map[string]func(*http.Server, *tls.Conn, http.Handler){}}
		go func() { log.Fatal(secure.ListenAndServeTLS(os.Args[3], os.Args[4])) }()
	}
	server := &http.Server{Addr: "127.0.0.1:" + os.Args[1], Handler: mux, ConnState: count}
	log.Fatal(server.ListenAndServe())
}
