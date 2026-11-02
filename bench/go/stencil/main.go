// Idiomatic parallel Go: NumCPU goroutines over contiguous chunks, ping-pong buffers.
package main

import (
	"fmt"
	"os"
	"runtime"
	"strconv"
	"sync"
)

func parFor(n int, body func(lo, hi int)) {
	workers := runtime.NumCPU()
	var wg sync.WaitGroup
	for t := 0; t < workers; t++ {
		lo, hi := n*t/workers, n*(t+1)/workers
		wg.Add(1)
		go func() { defer wg.Done(); body(lo, hi) }()
	}
	wg.Wait()
}

func stencil(xs, out []int64) {
	n := len(xs)
	parFor(n, func(lo, hi int) {
		for i := lo; i < hi; i++ {
			if i == 0 || i+1 == n {
				out[i] = xs[i]
			} else {
				out[i] = (xs[i-1] + 2*xs[i] + xs[i+1]) % 1000003
			}
		}
	})
}

func main() {
	if len(os.Args) != 3 {
		fmt.Fprintln(os.Stderr, "usage: stencil n iters")
		os.Exit(2)
	}
	n64, _ := strconv.ParseInt(os.Args[1], 10, 64)
	iters, _ := strconv.ParseInt(os.Args[2], 10, 64)
	n := int(n64)
	a := make([]int64, n)
	b := make([]int64, n)
	parFor(n, func(lo, hi int) {
		for i := lo; i < hi; i++ {
			a[i] = (int64(i) * 2654435761) % 1000003
		}
	})
	for k := int64(0); k < iters; k++ {
		stencil(a, b)
		a, b = b, a
	}
	partial := make([]int64, runtime.NumCPU())
	workers := runtime.NumCPU()
	var wg sync.WaitGroup
	for t := 0; t < workers; t++ {
		lo, hi := n*t/workers, n*(t+1)/workers
		wg.Add(1)
		go func(t, lo, hi int) {
			defer wg.Done()
			var s int64
			for i := lo; i < hi; i++ {
				s += a[i]
			}
			partial[t] = s
		}(t, lo, hi)
	}
	wg.Wait()
	var total int64
	for _, s := range partial {
		total += s
	}
	fmt.Println(total)
}
