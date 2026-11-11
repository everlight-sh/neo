// Loopback peers for the network stream's Neo drivers (tests/drivers/*.neo). They
// replace the Python ssl/socket peers of the retired scripts (in the v0.2.3 tag).
// Every mode listens on 127.0.0.1:0 and first prints "port N". Modes:
//
//	keepalive  http_keepalive.py: /chunked, /close (Connection: close), /drop (closed
//	           with no warning, as an idle timeout would), /big (5000 bytes), /post
//	           (the body length), otherwise the path without its slash.
//	largebody  http_large_body.py: /n/SIZE, /excess/SIZE (10 bytes more than announced),
//	           /short/SIZE (half the body, then close), /split/SIZE (997-byte writes).
//	sse        agent_network.py: POST /stream with the expected headers and body,
//	           answered with an SSE body in 3-byte chunks.
//	delayed    async_protocols.py: /hold (until the client leaves, at most 3 s),
//	           /tls (300 ms), /http (150 ms), otherwise 3 s; then "TLS OK" or "HTTP OK".
//	echo       tls_language.py's TLS peer: reads "Neo TLS\n", answers "secure echo\n".
//	           -case close|legacy|handshake-tag|application-tag|truncated|no-close|timeout.
//	proxy      tls12_language.py's TLS-aware proxy to -upstream PORT, rewriting with
//	           -hello, -flight and -record hooks (see the hook functions), -chunk N.
//	h2script   http2_language.py's scripted HTTP/2 server (TLS with ALPN h2, -cert and
//	           -key): frames written by hand for paths such as /ping, /padded,
//	           /trailers, /early, /rst, /refuse, /goaway-zero (see h2respond). It notes
//	           "request METHOD PATH" for each request it answers.
//
// -tls 1.3 or 1.2 (with -cert and -key) serves TLS with ALPN http/1.1; -fragment N
// writes the server's bytes N at a time. When stdin closes, the peer stops and
// prints its notes ("suite NAME", "version NAME", "received TEXT", "server_random
// HEX", "error TEXT"), then "accepted N" and "done".
//
//	go build -trimpath -o peer tests/fixtures/network_peer.go
package main

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha256"
	"crypto/tls"
	"encoding/binary"
	"encoding/hex"
	"errors"
	"flag"
	"fmt"
	"io"
	"net"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"sync"
	"time"
)

var (
	mode     = flag.String("mode", "", "keepalive, largebody, sse, delayed, echo, proxy or h2script")
	version  = flag.String("tls", "", "1.3 or 1.2")
	certFile = flag.String("cert", "", "certificate chain (PEM)")
	keyFile  = flag.String("key", "", "private key (PEM)")
	caseName = flag.String("case", "normal", "echo behaviour")
	fragment = flag.Int("fragment", 0, "write the server's bytes this many at a time")
	upstream = flag.Int("upstream", 0, "proxy: the upstream port")
	hello    = flag.String("hello", "", "proxy: strip:EXT")
	flight   = flag.String("flight", "", "proxy: server flight hook")
	record   = flag.String("record", "", "proxy: server record hook")
	chunk    = flag.Int("chunk", 0, "proxy: TCP write size towards the client")
	keylog   = flag.String("keylog", "", "proxy: the upstream server's key log")
)

var (
	mu       sync.Mutex
	accepted int
	notes    []string
)

func note(format string, args ...any) {
	mu.Lock()
	notes = append(notes, fmt.Sprintf(format, args...))
	mu.Unlock()
}

func failed(format string, args ...any) { note("error "+format, args...) }

func writeChunks(c net.Conn, data []byte, size int) error {
	if size <= 0 {
		size = len(data) + 1
	}
	for at := 0; at < len(data); at += size {
		end := at + size
		if end > len(data) {
			end = len(data)
		}
		if _, err := c.Write(data[at:end]); err != nil {
			return err
		}
	}
	return nil
}

// wire is the raw connection under a TLS server: it fragments writes and
// corrupts the first encrypted handshake record or the first application write.
type wire struct {
	net.Conn
	fragment        int
	mutateHandshake bool
	handshakeDone   bool
	app             string
}

func (w *wire) Write(b []byte) (int, error) {
	data := append([]byte(nil), b...)
	if !w.handshakeDone && w.mutateHandshake {
		for p := 0; p+5 <= len(data); {
			size := int(binary.BigEndian.Uint16(data[p+3:]))
			if data[p] == 23 && p+5+size <= len(data) {
				data[p+4+size] ^= 1
				w.mutateHandshake = false
				break
			}
			p += 5 + size
		}
	}
	if w.handshakeDone && len(data) > 0 {
		switch w.app {
		case "application-tag":
			data[len(data)-1] ^= 1
			w.app = ""
		case "truncated":
			data = data[:len(data)/2]
			w.app = ""
		}
	}
	if err := writeChunks(w.Conn, data, w.fragment); err != nil {
		return 0, err
	}
	return len(b), nil
}

func tlsConfig() *tls.Config {
	if *version == "" {
		return nil
	}
	cert, err := tls.LoadX509KeyPair(*certFile, *keyFile)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	c := &tls.Config{Certificates: []tls.Certificate{cert}, NextProtos: []string{"http/1.1"}}
	if *version == "1.2" {
		c.MinVersion, c.MaxVersion = tls.VersionTLS12, tls.VersionTLS12
	} else {
		c.MinVersion, c.MaxVersion = tls.VersionTLS13, tls.VersionTLS13
	}
	return c
}

// ---- HTTP/1.1 peers ----

type request struct {
	method, path, head string
	body               []byte
}

// readRequest reads one request after buffered; ok is false once the client is gone.
func readRequest(c net.Conn, buffered *[]byte) (request, bool) {
	tmp := make([]byte, 65536)
	for !bytes.Contains(*buffered, []byte("\r\n\r\n")) {
		n, err := c.Read(tmp)
		if n == 0 && err != nil {
			return request{}, false
		}
		*buffered = append(*buffered, tmp[:n]...)
	}
	at := bytes.Index(*buffered, []byte("\r\n\r\n"))
	head := string((*buffered)[:at])
	rest := append([]byte(nil), (*buffered)[at+4:]...)
	lines := strings.Split(head, "\r\n")
	parts := strings.Split(lines[0], " ")
	if len(parts) != 3 {
		failed("bad request line %q", lines[0])
		return request{}, false
	}
	length := 0
	for _, line := range lines[1:] {
		if strings.HasPrefix(strings.ToLower(line), "content-length:") {
			length, _ = strconv.Atoi(strings.TrimSpace(line[15:]))
			break
		}
	}
	for len(rest) < length {
		n, err := c.Read(tmp)
		if n == 0 && err != nil {
			return request{}, false
		}
		rest = append(rest, tmp[:n]...)
	}
	*buffered = append([]byte(nil), rest[length:]...)
	return request{parts[0], parts[1], head, rest[:length]}, true
}

func reply(c net.Conn, body []byte, extra string) error {
	_, err := c.Write(append([]byte(fmt.Sprintf("HTTP/1.1 200 OK\r\nContent-Length: %d\r\n%s\r\n", len(body), extra)), body...))
	return err
}

func keepalive(c net.Conn) {
	var buffered []byte
	for {
		r, ok := readRequest(c, &buffered)
		if !ok {
			return
		}
		switch r.path {
		case "/chunked":
			c.Write([]byte("HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n4\r\nchun\r\n4\r\nked!\r\n0\r\n\r\n"))
		case "/close":
			reply(c, []byte("close"), "Connection: close\r\n")
			return
		case "/drop":
			reply(c, []byte("drop"), "")
			return
		case "/big":
			reply(c, bytes.Repeat([]byte("x"), 5000), "")
		case "/post":
			if r.method != "POST" {
				failed("/post with %s", r.method)
			}
			reply(c, []byte(strconv.Itoa(len(r.body))), "")
		default:
			reply(c, []byte(r.path[1:]), "")
		}
	}
}

func largeBody(size int) []byte {
	b := make([]byte, size)
	for i := range b {
		b[i] = byte((i*31 + (i >> 8)) & 255)
	}
	return b
}

func largebody(c net.Conn) {
	var buffered []byte
	for {
		r, ok := readRequest(c, &buffered)
		if !ok {
			return
		}
		parts := strings.Split(r.path[1:], "/")
		size, _ := strconv.Atoi(parts[1])
		head := []byte(fmt.Sprintf("HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n", size))
		body := largeBody(size)
		switch parts[0] {
		case "n":
			c.Write(append(head, body...))
		case "excess":
			c.Write(append(append(head, body...), "0123456789"...))
		case "short":
			c.Write(append(head, body[:size/2]...))
			return
		default:
			c.Write(head)
			for at := 0; at < size; at += 997 {
				end := at + 997
				if end > size {
					end = size
				}
				c.Write(body[at:end])
			}
		}
	}
}

func sse(c net.Conn) {
	var buffered []byte
	r, ok := readRequest(c, &buffered)
	if !ok {
		failed("sse: no request")
		return
	}
	if !strings.Contains(r.head, "POST /stream HTTP/1.1") || !strings.Contains(r.head, "Authorization: Bearer test-token") ||
		!strings.Contains(r.head, "Content-Type: application/json") || string(r.body) != `{"question":42}` {
		failed("sse: unexpected request %q %q", r.head, r.body)
		return
	}
	body := []byte("id: 1\r\ndata: héllo\r\n\r\nevent: tool\ndata: second\n\n")
	c.Write([]byte("HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nTransfer-Encoding: chunked\r\n\r\n"))
	for at := 0; at < len(body); at += 3 {
		end := at + 3
		if end > len(body) {
			end = len(body)
		}
		c.Write([]byte(fmt.Sprintf("%x\r\n%s\r\n", end-at, body[at:end])))
	}
	c.Write([]byte("0\r\n\r\n"))
}

func delayed(c net.Conn, raw net.Conn) {
	var buffered []byte
	r, ok := readRequest(c, &buffered)
	if !ok {
		return
	}
	wait := 3 * time.Second
	switch r.path {
	case "/tls":
		wait = 300 * time.Millisecond
	case "/http":
		wait = 150 * time.Millisecond
	}
	if r.path == "/hold" {
		raw.SetReadDeadline(time.Now().Add(wait))
		one := make([]byte, 1)
		if _, err := raw.Read(one); err != nil {
			var timeout net.Error
			if !errors.As(err, &timeout) || !timeout.Timeout() {
				return
			}
		}
	} else {
		time.Sleep(wait)
	}
	body := []byte("HTTP OK")
	if r.path == "/tls" {
		body = []byte("TLS OK")
	}
	reply(c, body, "Connection: close\r\n")
}

// serve accepts connections until stdin closes, handing each (after a TLS
// handshake when configured) to handle together with the raw connection.
func serve(ln net.Listener, cfg *tls.Config, handle func(net.Conn, net.Conn)) {
	var wg sync.WaitGroup
	for {
		raw, err := ln.Accept()
		if err != nil {
			break
		}
		mu.Lock()
		accepted++
		mu.Unlock()
		wg.Add(1)
		go func() {
			defer wg.Done()
			defer raw.Close()
			raw.SetDeadline(time.Now().Add(20 * time.Second))
			var c net.Conn = raw
			if cfg != nil {
				s := tls.Server(&wire{Conn: raw, fragment: *fragment}, cfg)
				if err := s.Handshake(); err != nil {
					failed("handshake: %v", err)
					return
				}
				note("suite %s", tls.CipherSuiteName(s.ConnectionState().CipherSuite))
				c = s
			}
			handle(c, raw)
		}()
	}
	finished := make(chan struct{})
	go func() { wg.Wait(); close(finished) }()
	select {
	case <-finished:
	case <-time.After(3 * time.Second):
		failed("a connection was still being served")
	}
}

// ---- tls_language.py's echo peer ----

func echo(ln net.Listener, cfg *tls.Config) {
	raw, err := ln.Accept()
	if err != nil {
		return
	}
	mu.Lock()
	accepted++
	mu.Unlock()
	defer raw.Close()
	raw.SetDeadline(time.Now().Add(5 * time.Second))
	w := &wire{Conn: raw, fragment: *fragment, mutateHandshake: *caseName == "handshake-tag", app: *caseName}
	s := tls.Server(w, cfg)
	if err := s.Handshake(); err != nil {
		failed("handshake: %v", err)
		return
	}
	state := s.ConnectionState()
	note("version %s", tls.VersionName(state.Version))
	note("suite %s", tls.CipherSuiteName(state.CipherSuite))
	w.handshakeDone = true
	var message []byte
	buf := make([]byte, 16384)
	for !bytes.HasSuffix(message, []byte("\n")) {
		n, err := s.Read(buf)
		if n == 0 && err != nil {
			failed("read: %v", err)
			return
		}
		message = append(message, buf[:n]...)
	}
	note("received %s", strings.TrimSuffix(string(message), "\n"))
	if *caseName == "timeout" {
		time.Sleep(2500 * time.Millisecond)
		return
	}
	if _, err := s.Write([]byte("secure echo\n")); err != nil {
		failed("write: %v", err)
		return
	}
	switch *caseName {
	case "no-close", "truncated", "application-tag":
		return
	case "close":
		s.Close()
		return
	}
	s.Read(buf) // a graceful close from the client
}

// ---- tls12_language.py's proxy ----

func frame(kind byte, payload []byte, size int, ver []byte) []byte {
	var out []byte
	for i := 0; i < len(payload); i += size {
		end := i + size
		if end > len(payload) {
			end = len(payload)
		}
		out = append(out, kind, ver[0], ver[1], byte((end-i)>>8), byte(end-i))
		out = append(out, payload[i:end]...)
	}
	return out
}

func frame22(payload []byte) []byte { return frame(22, payload, 16384, []byte{3, 3}) }

func readRecord(c net.Conn, buf []byte) ([]byte, []byte) {
	tmp := make([]byte, 65536)
	for {
		if len(buf) >= 5 {
			size := int(binary.BigEndian.Uint16(buf[3:5]))
			if len(buf) >= 5+size {
				return append([]byte(nil), buf[:5+size]...), append([]byte(nil), buf[5+size:]...)
			}
		}
		n, err := c.Read(tmp)
		if n == 0 || (err != nil && n == 0) {
			return nil, buf
		}
		buf = append(buf, tmp[:n]...)
	}
}

func u24(v int) []byte { return []byte{byte(v >> 16), byte(v >> 8), byte(v)} }

func clientHelloExtensionsAt(m []byte) int {
	at := 38
	at += 1 + int(m[at])
	at += 2 + int(binary.BigEndian.Uint16(m[at:]))
	at += 1 + int(m[at])
	return at
}

func serverHelloExtensionsAt(m []byte) int { return 39 + int(m[38]) + 3 }

type extension struct {
	kind  int
	value []byte
}

func extensions(m []byte, at int) []extension {
	end := at + 2 + int(binary.BigEndian.Uint16(m[at:]))
	var out []extension
	for p := at + 2; p < end; {
		kind := int(binary.BigEndian.Uint16(m[p:]))
		size := int(binary.BigEndian.Uint16(m[p+2:]))
		out = append(out, extension{kind, m[p+4 : p+4+size]})
		p += 4 + size
	}
	return out
}

func editExtensions(m []byte, at int, edit func([]extension) []extension) []byte {
	var body []byte
	for _, e := range edit(extensions(m, at)) {
		body = append(body, byte(e.kind>>8), byte(e.kind), byte(len(e.value)>>8), byte(len(e.value)))
		body = append(body, e.value...)
	}
	inner := append(append(append([]byte(nil), m[4:at]...), byte(len(body)>>8), byte(len(body))), body...)
	return append(append([]byte{m[0]}, u24(len(inner))...), inner...)
}

func without(kind int) func([]extension) []extension {
	return func(items []extension) []extension {
		var out []extension
		for _, e := range items {
			if e.kind != kind {
				out = append(out, e)
			}
		}
		return out
	}
}

type proxy struct {
	clientRandom, serverRandom, clientSid []byte
	gone                                  bool
}

func (p *proxy) send(c net.Conn, data []byte) bool {
	if writeChunks(c, data, *chunk) != nil {
		p.gone = true
	}
	return !p.gone
}

func editMessages(messages [][]byte, kind byte, edit func([]byte) []byte) []byte {
	var all []byte
	for _, m := range messages {
		if m[0] == kind {
			m = edit(m)
		}
		all = append(all, m...)
	}
	return frame22(all)
}

// flightHook rewrites the server's plaintext handshake messages up to ServerHelloDone.
func (p *proxy) flightHook(messages [][]byte) ([]byte, bool) {
	serverHello := func(edit func([]extension) []extension) []byte {
		return editMessages(messages, 2, func(m []byte) []byte { return editExtensions(m, serverHelloExtensionsAt(m), edit) })
	}
	switch *flight {
	case "fragmented":
		return frame(22, bytes.Join(messages, nil), 7, []byte{3, 3}), false
	case "ske-flip-last":
		return editMessages(messages, 12, func(m []byte) []byte { m = append([]byte(nil), m...); m[len(m)-1] ^= 1; return m }), false
	case "ske-flip-point":
		return editMessages(messages, 12, func(m []byte) []byte { m = append([]byte(nil), m...); m[9] ^= 1; return m }), false
	case "sh-no-reneg":
		return serverHello(without(0xff01)), false
	case "sh-reneg-not-empty":
		return serverHello(func(items []extension) []extension {
			for i := range items {
				if items[i].kind == 0xff01 {
					items[i].value = append([]byte{12}, make([]byte, 12)...)
				}
			}
			return items
		}), false
	case "sh-no-ems":
		return serverHello(without(23)), false
	case "sh-ticket":
		return serverHello(func(items []extension) []extension { return append(items, extension{35, nil}) }), false
	case "echo-session":
		return editMessages(messages, 2, func(m []byte) []byte {
			old := int(m[38])
			inner := append(append(append(append([]byte(nil), m[4:38]...), byte(len(p.clientSid))), p.clientSid...), m[39+old:]...)
			return append(append([]byte{m[0]}, u24(len(inner))...), inner...)
		}), false
	case "early-ccs":
		return append(append(frame22(messages[0]), 0x14, 3, 3, 0, 1, 1), frame22(bytes.Join(messages[1:], nil))...), false
	case "truncate-flight":
		w := frame22(bytes.Join(messages, nil))
		return w[:len(w)/2], true
	}
	return frame22(bytes.Join(messages, nil)), false
}

func openssl(input []byte, args ...string) []byte {
	cmd := exec.Command("openssl", args...)
	cmd.Stdin = bytes.NewReader(input)
	out, err := cmd.Output()
	if err != nil {
		panic(fmt.Sprintf("openssl %v: %v", args, err))
	}
	return out
}

func chacha(key, nonce []byte, counter uint32, data []byte) []byte {
	iv := binary.LittleEndian.AppendUint32(nil, counter)
	return openssl(data, "enc", "-chacha20", "-K", hex.EncodeToString(key), "-iv", hex.EncodeToString(append(iv, nonce...)), "-nosalt")
}

func chachaSeal(key, nonce, aad, plain []byte) []byte {
	ciphertext := chacha(key, nonce, 1, plain)
	polykey := chacha(key, nonce, 0, make([]byte, 32))
	pad := func(n int) []byte { return make([]byte, (16-n%16)%16) }
	mac := append(append(append(append(append([]byte(nil), aad...), pad(len(aad))...), ciphertext...), pad(len(ciphertext))...),
		binary.LittleEndian.AppendUint64(binary.LittleEndian.AppendUint64(nil, uint64(len(aad))), uint64(len(ciphertext)))...)
	tag, _ := hex.DecodeString(strings.TrimSpace(string(openssl(mac, "mac", "-macopt", "hexkey:"+hex.EncodeToString(polykey), "POLY1305"))))
	return append(ciphertext, tag...)
}

func prf(secret, label, seed []byte, count int) []byte {
	mac := func(data []byte) []byte { h := hmac.New(sha256.New, secret); h.Write(data); return h.Sum(nil) }
	var out []byte
	a := append(append([]byte(nil), label...), seed...)
	for len(out) < count {
		a = mac(a)
		out = append(out, mac(append(append(append([]byte(nil), a...), label...), seed...))...)
	}
	return out[:count]
}

func masterSecret(clientRandom []byte) []byte {
	want := hex.EncodeToString(clientRandom)
	for i := 0; i < 100; i++ {
		if text, err := os.ReadFile(*keylog); err == nil {
			for _, line := range strings.Split(string(text), "\n") {
				parts := strings.Fields(line)
				if len(parts) == 3 && parts[0] == "CLIENT_RANDOM" && parts[1] == want {
					secret, _ := hex.DecodeString(parts[2])
					return secret
				}
			}
		}
		time.Sleep(20 * time.Millisecond)
	}
	panic("no CLIENT_RANDOM line in the server key log")
}

// recordHook sees each server record after its ChangeCipherSpec (index 0 is the Finished).
func (p *proxy) recordHook(index int, rec []byte) ([]byte, bool) {
	switch {
	case *record == "finished-control" || *record == "finished-forged":
		if index != 0 {
			return rec, false
		}
		block := prf(masterSecret(p.clientRandom), []byte("key expansion"), append(append([]byte(nil), p.serverRandom...), p.clientRandom...), 88)
		key, iv := block[32:64], block[76:88]
		plain := chacha(key, iv, 1, rec[5:len(rec)-16])
		if rec[0] != 22 || !bytes.HasPrefix(plain, []byte{0x14, 0, 0, 0x0c}) {
			panic("independent key derivation disagrees with OpenSSL: " + hex.EncodeToString(plain))
		}
		if *record == "finished-forged" {
			for i := 4; i < len(plain); i++ {
				plain[i] ^= 0x5a
			}
		}
		aad := append(make([]byte, 8), 0x16, 3, 3, byte(len(plain)>>8), byte(len(plain)))
		body := chachaSeal(key, iv, aad, plain)
		return append([]byte{0x16, 3, 3, byte(len(body) >> 8), byte(len(body))}, body...), false
	case *record == "corrupt-finished":
		if index == 0 {
			rec = append([]byte(nil), rec...)
			rec[len(rec)-3] ^= 1
		}
		return rec, false
	case strings.HasPrefix(*record, "truncate:"):
		at, _ := strconv.Atoi(strings.TrimPrefix(*record, "truncate:"))
		if index == at {
			return rec[:len(rec)/2], true
		}
	}
	return rec, false
}

func (p *proxy) clientToServer(client, up net.Conn) {
	rec, buf := readRecord(client, nil)
	if rec == nil {
		return
	}
	message := rec[5:]
	if message[0] != 1 {
		failed("expected ClientHello")
		return
	}
	p.clientRandom = append([]byte(nil), message[6:38]...)
	p.clientSid = append([]byte(nil), message[39:39+int(message[38])]...)
	if strings.HasPrefix(*hello, "strip:") {
		kind, _ := strconv.Atoi(strings.TrimPrefix(*hello, "strip:"))
		message = editExtensions(message, clientHelloExtensionsAt(message), without(kind))
	}
	if _, err := up.Write(append(frame(22, message, 16384, rec[1:3]), buf...)); err != nil {
		return
	}
	io.Copy(up, client)
	if t, ok := up.(*net.TCPConn); ok {
		t.CloseWrite()
	}
}

func (p *proxy) serverToClient(up, client net.Conn) {
	var buf, handshake []byte
	var messages [][]byte
	encrypted, index := false, 0
	for {
		var rec []byte
		rec, buf = readRecord(up, buf)
		if rec == nil {
			return
		}
		kind := rec[0]
		if encrypted {
			out, stop := p.recordHook(index, rec)
			index++
			if !p.send(client, out) || stop {
				return
			}
			continue
		}
		if kind == 20 {
			encrypted = true
			if !p.send(client, rec) {
				return
			}
			continue
		}
		if kind != 22 {
			if !p.send(client, rec) {
				return
			}
			continue
		}
		handshake = append(handshake, rec[5:]...)
		for len(handshake) >= 4 && len(handshake) >= 4+int(handshake[1])<<16+int(handshake[2])<<8+int(handshake[3]) {
			size := 4 + int(handshake[1])<<16 + int(handshake[2])<<8 + int(handshake[3])
			message := append([]byte(nil), handshake[:size]...)
			handshake = handshake[size:]
			if message[0] == 2 {
				p.serverRandom = append([]byte(nil), message[6:38]...)
			}
			messages = append(messages, message)
			if message[0] == 14 {
				out, stop := p.flightHook(messages)
				messages = nil
				if !p.send(client, out) || stop {
					return
				}
			}
		}
	}
}

func runProxy(ln net.Listener) {
	client, err := ln.Accept()
	if err != nil {
		return
	}
	mu.Lock()
	accepted++
	mu.Unlock()
	up, err := net.DialTimeout("tcp", fmt.Sprintf("127.0.0.1:%d", *upstream), 15*time.Second)
	if err != nil {
		failed("upstream: %v", err)
		client.Close()
		return
	}
	client.SetDeadline(time.Now().Add(15 * time.Second))
	up.SetDeadline(time.Now().Add(15 * time.Second))
	p := &proxy{}
	pumped := make(chan struct{})
	go func() { defer close(pumped); p.clientToServer(client, up) }()
	func() {
		defer func() {
			if r := recover(); r != nil {
				failed("server->client: %v", r)
			}
		}()
		p.serverToClient(up, client)
	}()
	if t, ok := client.(*net.TCPConn); ok {
		t.CloseRead()
		t.CloseWrite()
	}
	if t, ok := up.(*net.TCPConn); ok {
		t.CloseRead()
		t.CloseWrite()
	}
	select {
	case <-pumped:
	case <-time.After(5 * time.Second):
	}
	client.Close()
	up.Close()
	if p.serverRandom != nil {
		note("server_random %s", hex.EncodeToString(p.serverRandom))
	}
}

// ---- h2script: a scripted HTTP/2 server ----

// h2fail is a failed expectation about what the client sent (noted as an error);
// h2gone ends a connection quietly.
type h2fail string
type h2gone struct{}

func h2check(ok bool, message string) {
	if !ok {
		panic(h2fail(message))
	}
}

// The static table entries the client uses.
var h2static = map[int][2]string{1: {":authority", ""}, 2: {":method", "GET"}, 3: {":method", "POST"}, 4: {":path", "/"},
	5: {":path", "/index.html"}, 6: {":scheme", "http"}, 7: {":scheme", "https"}, 28: {"content-length", ""}}

var h2paths []string

// h2seen records a request and returns how many requests for path there have been.
func h2seen(method, path string) int {
	mu.Lock()
	defer mu.Unlock()
	notes = append(notes, "request "+method+" "+path)
	h2paths = append(h2paths, path)
	n := 0
	for _, p := range h2paths {
		if p == path {
			n++
		}
	}
	return n
}

func h2frame(kind, flags byte, stream uint32, payload []byte) []byte {
	out := []byte{byte(len(payload) >> 16), byte(len(payload) >> 8), byte(len(payload)), kind, flags}
	out = binary.BigEndian.AppendUint32(out, stream)
	return append(out, payload...)
}

func h2literal(name, value string, prefix byte) []byte {
	h2check(len(name) < 127 && len(value) < 127, "literal too long")
	out := append([]byte{prefix, byte(len(name))}, name...)
	return append(append(out, byte(len(value))), value...)
}

func h2int(block []byte, at int, prefix uint) (int, int) {
	h2check(at < len(block), "truncated header block")
	mask := 1<<prefix - 1
	value := int(block[at]) & mask
	at++
	if value < mask {
		return value, at
	}
	for shift := 0; ; shift += 7 {
		h2check(at < len(block), "truncated header block")
		b := block[at]
		at++
		value += int(b&127) << shift
		if b < 128 {
			return value, at
		}
	}
}

func h2string(block []byte, at int) (string, int) {
	h2check(at < len(block) && block[at]&0x80 == 0, "the client does not Huffman-code")
	size, at := h2int(block, at, 7)
	h2check(at+size <= len(block), "truncated header block")
	return string(block[at : at+size]), at + size
}

// h2decode decodes a request's header block: static indices and literals without indexing.
func h2decode(block []byte) map[string]string {
	fields := map[string]string{}
	for at := 0; at < len(block); {
		if block[at]&0x80 != 0 {
			var index int
			index, at = h2int(block, at, 7)
			entry, ok := h2static[index]
			h2check(ok, fmt.Sprintf("static index %d", index))
			fields[entry[0]] = entry[1]
			continue
		}
		h2check(block[at]&0xe0 == 0, "the client sends literals without indexing")
		var index int
		index, at = h2int(block, at, 4)
		var name string
		if index != 0 {
			entry, ok := h2static[index]
			h2check(ok, fmt.Sprintf("static index %d", index))
			name = entry[0]
		} else {
			name, at = h2string(block, at)
		}
		var value string
		value, at = h2string(block, at)
		fields[name] = value
	}
	return fields
}

type h2conn struct {
	c   net.Conn
	buf []byte
}

func (h *h2conn) read(n int) []byte {
	tmp := make([]byte, 65536)
	for len(h.buf) < n {
		got, err := h.c.Read(tmp)
		if got == 0 && err != nil {
			panic(h2gone{})
		}
		h.buf = append(h.buf, tmp[:got]...)
	}
	out := append([]byte(nil), h.buf[:n]...)
	h.buf = h.buf[n:]
	return out
}

func (h *h2conn) frame() (byte, byte, uint32, []byte) {
	head := h.read(9)
	size := int(head[0])<<16 | int(head[1])<<8 | int(head[2])
	return head[3], head[4], binary.BigEndian.Uint32(head[5:9]) & 0x7fffffff, h.read(size)
}

func (h *h2conn) send(frames ...[]byte) {
	if _, err := h.c.Write(bytes.Join(frames, nil)); err != nil {
		panic(h2gone{})
	}
}

// waitFor reads frames, acknowledging SETTINGS, until done holds.
func (h *h2conn) waitFor(done func(kind, flags byte, payload []byte) bool) {
	for {
		kind, flags, _, payload := h.frame()
		if kind == 4 && flags&1 == 0 {
			h.send(h2frame(4, 1, 0, nil))
		}
		if done(kind, flags, payload) {
			return
		}
	}
}

func h2settings(pairs ...uint32) []byte {
	var out []byte
	for i := 0; i+1 < len(pairs); i += 2 {
		out = binary.BigEndian.AppendUint16(out, uint16(pairs[i]))
		out = binary.BigEndian.AppendUint32(out, pairs[i+1])
	}
	return out
}

func (h *h2conn) serve() {
	h2check(string(h.read(24)) == "PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n", "no HTTP/2 preface")
	h.send(h2frame(4, 0, 0, h2settings(3, 100)))
	type pending struct {
		fields map[string]string
		body   []byte
	}
	requests := map[uint32]*pending{}
	for {
		kind, flags, stream, payload := h.frame()
		switch {
		case kind == 4 && flags&1 == 0:
			settings := map[uint16]uint32{}
			for i := 0; i+6 <= len(payload); i += 6 {
				settings[binary.BigEndian.Uint16(payload[i:])] = binary.BigEndian.Uint32(payload[i+2:])
			}
			push, pushed := settings[2]
			window, windowed := settings[4]
			h2check(pushed && push == 0 && windowed && window == 16777216, fmt.Sprintf("client SETTINGS %v", settings))
			h.send(h2frame(4, 1, 0, nil))
		case kind == 1:
			h2check(flags&4 != 0 && stream%2 == 1, "one HEADERS frame per request")
			requests[stream] = &pending{fields: h2decode(payload)}
			if flags&1 != 0 {
				r := requests[stream]
				delete(requests, stream)
				h.respond(stream, r.fields, r.body)
			}
		case kind == 0 && requests[stream] != nil:
			requests[stream].body = append(requests[stream].body, payload...)
			if flags&1 != 0 {
				r := requests[stream]
				delete(requests, stream)
				h.respond(stream, r.fields, r.body)
			}
		case kind == 7:
			return
		}
	}
}

func (h *h2conn) respond(stream uint32, fields map[string]string, body []byte) {
	path := fields[":path"]
	count := h2seen(fields[":method"], path)
	length, ok := fields["content-length"]
	if !ok {
		length = "-"
	}
	summary := strings.Join([]string{fields[":method"], path, fields[":authority"], fields[":scheme"], length}, " ")
	okBlock := append([]byte{0x88}, h2literal("x-neo-request", summary, 0)...)
	join := func(parts ...[]byte) []byte { return bytes.Join(parts, nil) }
	switch {
	case path == "/ping":
		h.send(h2frame(4, 0, 0, h2settings(4, 1<<20)), h2frame(6, 0, 0, []byte("neo-ping")))
		acks := map[byte]bool{}
		h.waitFor(func(kind, flags byte, payload []byte) bool {
			if flags&1 != 0 && (kind == 4 || kind == 6 && string(payload) == "neo-ping") {
				acks[kind] = true
			}
			return acks[4] && acks[6]
		})
		h.send(h2frame(1, 4, stream, join(okBlock, h2literal("x-neo-ping", "acked", 0))), h2frame(0, 1, stream, []byte("pong")))
	case path == "/padded":
		block := join(okBlock, h2literal("x-neo-padded", "yes", 0))
		h.send(h2frame(1, 8|32, stream, join([]byte{10}, []byte{0, 0, 0, 0, 15}, block[:5], make([]byte, 10))),
			h2frame(9, 0, stream, block[5:12]), h2frame(9, 4, stream, block[12:]),
			h2frame(0, 8, stream, join([]byte{3}, []byte("abc"), make([]byte, 3))), h2frame(0, 0, stream, nil),
			h2frame(0, 8|1, stream, join([]byte{200}, []byte("defgh"), make([]byte, 200))))
	case path == "/trailers":
		h.send(h2frame(1, 4, stream, okBlock), h2frame(0, 0, stream, []byte("body")), h2frame(1, 5, stream, h2literal("x-neo-trailer", "yes", 0)))
	case path == "/early":
		h.send(h2frame(1, 4, stream, join([]byte("\x00\x07:status\x03103"), h2literal("link", "</a.css>; rel=preload", 0))),
			h2frame(1, 4, stream, join(okBlock, h2literal("x-neo-final", "yes", 0))), h2frame(0, 1, stream, []byte("final")))
	case path == "/size-update":
		h.send(h2frame(1, 5, stream, join([]byte{0x20, 0x3f, 0xe1, 0x1f}, okBlock, h2literal("x-neo-indexed", "first", 0x40))))
	case path == "/size-again":
		h.send(h2frame(1, 5, stream, join(okBlock, []byte{0xbe})))
	case path == "/rst":
		h.send(h2frame(3, 0, stream, []byte{0, 0, 0, 2}))
	case path == "/refuse" && count == 1:
		h.send(h2frame(3, 0, stream, []byte{0, 0, 0, 7}))
	case path == "/goaway-zero" && count == 1:
		h.send(h2frame(7, 0, 0, make([]byte, 8)))
		panic(h2gone{})
	case path == "/goaway-after":
		h.send(h2frame(1, 5, stream, okBlock), h2frame(7, 0, 0, binary.BigEndian.AppendUint32(binary.BigEndian.AppendUint32(nil, stream), 0)))
		panic(h2gone{})
	case path == "/bad-frame":
		h.send(h2frame(0, 0, 0, []byte("x")))
	case path == "/uppercase":
		h.send(h2frame(1, 5, stream, join(okBlock, h2literal("X-Neo-Upper", "no", 0))))
	default:
		if len(body) == 0 {
			body = []byte("plain")
		}
		h.send(h2frame(1, 4, stream, okBlock), h2frame(0, 1, stream, body))
	}
}

// h2handle serves one connection; like the script's ssl socket, it ends without close_notify.
func h2handle(raw net.Conn, cfg *tls.Config) {
	defer raw.Close()
	defer func() {
		if r := recover(); r != nil {
			if message, ok := r.(h2fail); ok {
				failed("%s", string(message))
			} else if _, ok := r.(h2gone); !ok {
				failed("h2script: %v", r)
			}
		}
	}()
	c := tls.Server(raw, cfg)
	raw.SetDeadline(time.Now().Add(60 * time.Second))
	if err := c.Handshake(); err != nil {
		return
	}
	h2check(c.ConnectionState().NegotiatedProtocol == "h2", "ALPN did not select h2")
	(&h2conn{c: c}).serve()
}

func h2script(ln net.Listener) {
	cert, err := tls.LoadX509KeyPair(*certFile, *keyFile)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	cfg := &tls.Config{Certificates: []tls.Certificate{cert}, NextProtos: []string{"h2"}}
	for {
		c, err := ln.Accept()
		if err != nil {
			return
		}
		mu.Lock()
		accepted++
		mu.Unlock()
		go h2handle(c, cfg)
	}
}

func main() {
	flag.Parse()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	fmt.Printf("port %d\n", ln.Addr().(*net.TCPAddr).Port)
	cfg := tlsConfig()
	stopped := make(chan struct{})
	go func() {
		io.Copy(io.Discard, os.Stdin)
		ln.Close()
		close(stopped)
	}()
	plain := func(handle func(net.Conn)) func(net.Conn, net.Conn) {
		return func(c, _ net.Conn) { handle(c) }
	}
	switch *mode {
	case "keepalive":
		serve(ln, cfg, plain(keepalive))
	case "largebody":
		serve(ln, cfg, plain(largebody))
	case "sse":
		serve(ln, cfg, plain(sse))
	case "delayed":
		serve(ln, cfg, delayed)
	case "echo":
		echo(ln, cfg)
	case "proxy":
		runProxy(ln)
	case "h2script":
		h2script(ln)
	default:
		fmt.Fprintln(os.Stderr, "unknown -mode", *mode)
		os.Exit(2)
	}
	<-stopped
	mu.Lock()
	for _, n := range notes {
		fmt.Println(n)
	}
	fmt.Printf("accepted %d\ndone\n", accepted)
	mu.Unlock()
}
