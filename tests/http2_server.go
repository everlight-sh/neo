// An HTTPS test server for tests/http2_language.py and tests/tls_resume_language.py:
// http2_server -cert LEAF.pem -key LEAF.key [-h1]. It prints its port, then serves
// TLS with ALPN h2 and http/1.1 (only http/1.1 with -h1):
//
//	/hello        13 bytes, with X-Neo-Proto naming the request's protocol
//	/1m           1 MiB with a Content-Length (byte i is i mod 253)
//	/headers      100 X-Neo-H* fields and X-Neo-Ascii, enough to evict HPACK entries
//	/big-headers  one 30000-byte field, more than a 16 KiB frame (CONTINUATION)
//	/stream       50 flushed 10000-byte chunks without a Content-Length
//	/echo         the request body
//	/goaway       sets Connection: close, which over h2 sends GOAWAY
//	/conns        how many connections the server has accepted
package main

import (
	"crypto/tls"
	"flag"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"strconv"
	"strings"
	"sync/atomic"
)

func pattern(n, mod int) []byte {
	b := make([]byte, n)
	for i := range b {
		b[i] = byte(i % mod)
	}
	return b
}

// HeaderValue is the value of X-Neo-H<i>, which tests/http2_language.py repeats.
func headerValue(i int) string {
	return fmt.Sprintf("v%03d-%s", i, strings.Repeat(string(rune('a'+i%26)), 20+i%40))
}

func bigValue() string {
	const alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
	b := make([]byte, 30000)
	for i := range b {
		b[i] = alphabet[(i*7)%len(alphabet)]
	}
	return string(b)
}

func ascii() string {
	var b strings.Builder
	for c := 0x21; c <= 0x7e; c++ {
		b.WriteByte(byte(c))
		if c%16 == 0 {
			b.WriteByte(' ')
		}
	}
	return b.String()
}

func main() {
	cert := flag.String("cert", "", "certificate chain (PEM)")
	key := flag.String("key", "", "private key (PEM)")
	h1 := flag.Bool("h1", false, "offer only http/1.1")
	flag.Parse()
	var conns atomic.Int64
	big := pattern(1<<20, 253)
	mux := http.NewServeMux()
	mux.HandleFunc("/hello", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Neo-Proto", r.Proto)
		io.WriteString(w, "Hello, World!")
	})
	mux.HandleFunc("/1m", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Length", strconv.Itoa(len(big)))
		w.Write(big)
	})
	mux.HandleFunc("/headers", func(w http.ResponseWriter, r *http.Request) {
		for i := 0; i < 100; i++ {
			w.Header().Set(fmt.Sprintf("X-Neo-H%03d", i), headerValue(i))
		}
		w.Header().Set("X-Neo-Ascii", ascii())
		io.WriteString(w, "headers")
	})
	value := bigValue()
	mux.HandleFunc("/big-headers", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Neo-Big", value)
		io.WriteString(w, "big")
	})
	mux.HandleFunc("/stream", func(w http.ResponseWriter, r *http.Request) {
		chunk := pattern(10000, 241)
		for i := 0; i < 50; i++ {
			w.Write(chunk)
			w.(http.Flusher).Flush()
		}
	})
	mux.HandleFunc("/echo", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Neo-Method", r.Method)
		io.Copy(w, r.Body)
	})
	mux.HandleFunc("/goaway", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Connection", "close")
		io.WriteString(w, "bye")
	})
	mux.HandleFunc("/conns", func(w http.ResponseWriter, r *http.Request) { fmt.Fprint(w, conns.Load()) })
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		log.Fatal(err)
	}
	server := &http.Server{Handler: mux, ConnState: func(c net.Conn, state http.ConnState) {
		if state == http.StateNew {
			conns.Add(1)
		}
	}}
	if *h1 {
		server.TLSNextProto = map[string]func(*http.Server, *tls.Conn, http.Handler){}
	}
	fmt.Println(ln.Addr().(*net.TCPAddr).Port)
	log.Fatal(server.ServeTLS(ln, *cert, *key))
}
