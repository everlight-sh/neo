// GET with net/http COUNT times: client PORT PATH COUNT SIZE KEEP [CA.pem].
// KEEP 0 opens a connection per request, like fetch.neo; KEEP 1 reuses one.
// With a root certificate the requests use HTTPS. Prints the total
// nanoseconds and how many responses were 200 with SIZE bytes, then each
// request's nanoseconds.
package main

import (
	"crypto/tls"
	"crypto/x509"
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"
)

func main() {
	count, _ := strconv.Atoi(os.Args[3])
	size, _ := strconv.Atoi(os.Args[4])
	transport := &http.Transport{DisableKeepAlives: os.Args[5] != "1"}
	scheme := "http"
	if len(os.Args) > 6 {
		pem, err := os.ReadFile(os.Args[6])
		if err != nil {
			panic(err)
		}
		roots := x509.NewCertPool()
		roots.AppendCertsFromPEM(pem)
		transport.TLSClientConfig = &tls.Config{RootCAs: roots}
		scheme = "https"
	}
	client := &http.Client{Transport: transport, Timeout: 10 * time.Second}
	url := scheme + "://127.0.0.1:" + os.Args[1] + os.Args[2]
	times := make([]string, 0, count)
	good := 0
	start := time.Now()
	for i := 0; i < count; i++ {
		before := time.Now()
		response, err := client.Get(url)
		if err != nil {
			times = append(times, strconv.FormatInt(time.Since(before).Nanoseconds(), 10))
			continue
		}
		body, err := io.ReadAll(response.Body)
		response.Body.Close()
		times = append(times, strconv.FormatInt(time.Since(before).Nanoseconds(), 10))
		if err == nil && response.StatusCode == 200 && len(body) == size {
			good++
		}
	}
	fmt.Println(time.Since(start).Nanoseconds(), good)
	fmt.Println(strings.Join(times, " "))
}
