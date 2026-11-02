// Validation-first keep-alive/pipeline load client for the regression suite.
package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"os"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

func response(r *bufio.Reader) error {
	line, err := r.ReadSlice('\n')
	if err != nil {
		return err
	}
	if !bytes.HasPrefix(line, []byte("HTTP/1.1 200 ")) {
		return fmt.Errorf("unexpected status: %q", line)
	}
	length := -1
	for {
		line, err = r.ReadSlice('\n')
		if err != nil {
			return err
		}
		if bytes.Equal(line, []byte("\r\n")) {
			break
		}
		colon := bytes.IndexByte(line, ':')
		if colon < 1 {
			return fmt.Errorf("bad header")
		}
		if bytes.EqualFold(line[:colon], []byte("content-length")) {
			length, err = strconv.Atoi(strings.TrimSpace(string(line[colon+1:])))
			if err != nil {
				return err
			}
		}
	}
	if length != len("Hello, World!") {
		return fmt.Errorf("unexpected content length: %d", length)
	}
	var body [13]byte
	if _, err := io.ReadFull(r, body[:]); err != nil {
		return err
	}
	if string(body[:]) != "Hello, World!" {
		return fmt.Errorf("incorrect response body")
	}
	return nil
}

func main() {
	port := os.Args[1]
	connections, err := strconv.Atoi(os.Args[2])
	if err != nil {
		panic(err)
	}
	depth, err := strconv.Atoi(os.Args[3])
	if err != nil {
		panic(err)
	}
	if depth == 0 {
		depth = 1
	}
	duration, err := time.ParseDuration(os.Args[4])
	if err != nil {
		panic(err)
	}
	request := bytes.Repeat([]byte("GET / HTTP/1.1\r\nHost: localhost\r\nConnection: keep-alive\r\n\r\n"), depth)
	clients := make([]net.Conn, connections)
	for i := range clients {
		clients[i], err = net.DialTimeout("tcp", "127.0.0.1:"+port, 3*time.Second)
		if err != nil {
			panic(err)
		}
	}
	var requests atomic.Int64
	var failures atomic.Int64
	var first sync.Once
	var errorText string
	var ready sync.WaitGroup
	ready.Add(connections)
	var finished sync.WaitGroup
	finished.Add(connections)
	startSignal := make(chan struct{})
	var deadline time.Time
	for _, conn := range clients {
		go func(conn net.Conn) {
			defer finished.Done()
			defer conn.Close()
			r := bufio.NewReaderSize(conn, 32768)
			ready.Done()
			<-startSignal
			conn.SetDeadline(deadline.Add(3 * time.Second))
			fail := func(err error) { failures.Add(1); first.Do(func() { errorText = err.Error() }) }
			for time.Now().Before(deadline) {
				if _, err := io.Copy(conn, bytes.NewReader(request)); err != nil {
					fail(err)
					return
				}
				for i := 0; i < depth; i++ {
					if err := response(r); err != nil {
						fail(err)
						return
					}
					requests.Add(1)
				}
			}
		}(conn)
	}
	ready.Wait()
	started := time.Now()
	deadline = started.Add(duration)
	close(startSignal)
	finished.Wait()
	elapsed := time.Since(started)
	result := map[string]any{"requests": requests.Load(), "elapsed_ns": elapsed.Nanoseconds(), "rps": float64(requests.Load()) / elapsed.Seconds(), "errors": failures.Load(), "error": errorText}
	if err := json.NewEncoder(os.Stdout).Encode(result); err != nil {
		panic(err)
	}
	if failures.Load() != 0 {
		os.Exit(2)
	}
}
