// Idiomatic Go n-body: a slice of Body structs (array-of-structs), goroutines
// over contiguous chunks of bodies. Same model as examples/nbody.neo.
package main

import (
	"fmt"
	"math"
	"os"
	"runtime"
	"strconv"
	"sync"
)

type Body struct{ X, Y, Z, VX, VY, VZ, M float64 }

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

func initBodies(n int) []Body {
	bs := make([]Body, n)
	for i := range bs {
		k := int64(i)
		bs[i] = Body{
			X: float64((k*2654435761)%1009) / 1009.0,
			Y: float64((k*40503)%1013) / 1013.0,
			Z: float64((k*69069)%1019) / 1019.0,
			M: 1.0 / float64(n),
		}
	}
	return bs
}

func kick(bs []Body, dt float64) []Body {
	out := make([]Body, len(bs))
	parFor(len(bs), func(lo, hi int) {
		for i := lo; i < hi; i++ {
			b := bs[i]
			var ax, ay, az float64
			for j := range bs {
				o := &bs[j]
				dx, dy, dz := o.X-b.X, o.Y-b.Y, o.Z-b.Z
				d2 := dx*dx + dy*dy + dz*dz + 0.01
				inv := o.M / (d2 * math.Sqrt(d2))
				ax += dx * inv
				ay += dy * inv
				az += dz * inv
			}
			b.VX += ax * dt
			b.VY += ay * dt
			b.VZ += az * dt
			out[i] = b
		}
	})
	return out
}

func drift(bs []Body, dt float64) []Body {
	out := make([]Body, len(bs))
	parFor(len(bs), func(lo, hi int) {
		for i := lo; i < hi; i++ {
			b := bs[i]
			b.X += b.VX * dt
			b.Y += b.VY * dt
			b.Z += b.VZ * dt
			out[i] = b
		}
	})
	return out
}

func energy(bs []Body) float64 {
	partial := make([]float64, runtime.NumCPU())
	workers := runtime.NumCPU()
	var wg sync.WaitGroup
	for t := 0; t < workers; t++ {
		lo, hi := len(bs)*t/workers, len(bs)*(t+1)/workers
		wg.Add(1)
		go func(t, lo, hi int) {
			defer wg.Done()
			var e float64
			for i := lo; i < hi; i++ {
				b := bs[i]
				e += 0.5 * b.M * (b.VX*b.VX + b.VY*b.VY + b.VZ*b.VZ)
				var pot float64
				for j := range bs {
					if j != i {
						o := &bs[j]
						dx, dy, dz := o.X-b.X, o.Y-b.Y, o.Z-b.Z
						pot += b.M * o.M / math.Sqrt(dx*dx+dy*dy+dz*dz+0.01)
					}
				}
				e -= 0.5 * pot
			}
			partial[t] = e
		}(t, lo, hi)
	}
	wg.Wait()
	var e float64
	for _, p := range partial {
		e += p
	}
	return e
}

func main() {
	n, _ := strconv.Atoi(os.Args[1])
	steps, _ := strconv.Atoi(os.Args[2])
	bs := initBodies(n)
	for k := 0; k < steps; k++ {
		bs = drift(kick(bs, 0.001), 0.001)
	}
	fmt.Printf("%.17f\n", energy(bs))
}
