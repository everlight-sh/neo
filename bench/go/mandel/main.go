// Idiomatic parallel Go: one goroutine per row, WaitGroup, per-row results.
package main

import (
	"fmt"
	"os"
	"strconv"
	"sync"
)

func escape(cx, cy float64, max int64) int64 {
	zx, zy, k := 0.0, 0.0, int64(0)
	for k < max && zx*zx+zy*zy <= 4.0 {
		nx := zx*zx - zy*zy + cx
		zy = 2.0*zx*zy + cy
		zx = nx
		k++
	}
	return k
}

func main() {
	if len(os.Args) != 4 {
		fmt.Fprintln(os.Stderr, "usage: mandel w h max")
		os.Exit(2)
	}
	w, _ := strconv.ParseInt(os.Args[1], 10, 64)
	h, _ := strconv.ParseInt(os.Args[2], 10, 64)
	max, _ := strconv.ParseInt(os.Args[3], 10, 64)
	rows := make([]int64, h)
	var wg sync.WaitGroup
	for y := int64(0); y < h; y++ {
		wg.Add(1)
		go func(y int64) {
			defer wg.Done()
			cy := -1.5 + 3.0*float64(y)/float64(h)
			var acc int64
			for x := int64(0); x < w; x++ {
				acc += escape(-2.0+3.0*float64(x)/float64(w), cy, max)
			}
			rows[y] = acc
		}(y)
	}
	wg.Wait()
	var total int64
	for _, r := range rows {
		total += r
	}
	fmt.Println(total)
}
