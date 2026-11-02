// Idiomatic Go: net/http, goroutine per connection, keep-alive handled by the library.
// GET /smooth/N runs 32 passes of a 3-point stencil over an N-element signal and returns JSON.
package main

import (
	"encoding/json"
	"fmt"
	"math"
	"net/http"
	"os"
	"strconv"
	"strings"
)

const passes = 32

// ---- n-body for POST /nbody (sequential per request; the server is parallel across connections)
type Body struct{ X, Y, Z, VX, VY, VZ, M float64 }

func nbodyInit(n int) []Body {
	bs := make([]Body, n)
	for i := range bs {
		k := int64(i)
		bs[i] = Body{X: float64((k*2654435761)%1009) / 1009.0, Y: float64((k*40503)%1013) / 1013.0,
			Z: float64((k*69069)%1019) / 1019.0, M: 1.0 / float64(n)}
	}
	return bs
}

func nbodyStep(bs []Body, dt float64) []Body {
	out := make([]Body, len(bs))
	for i := range bs {
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
		b.X += b.VX * dt
		b.Y += b.VY * dt
		b.Z += b.VZ * dt
		out[i] = b
	}
	return out
}

func nbodyEnergy(bs []Body) float64 {
	var e float64
	for i := range bs {
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
	return e
}

func simulate(n, steps int) float64 {
	bs := nbodyInit(n)
	for k := 0; k < steps; k++ {
		bs = nbodyStep(bs, 0.001)
	}
	return nbodyEnergy(bs)
}

func stencil(xs, out []int64) {
	n := len(xs)
	for i := 0; i < n; i++ {
		if i == 0 || i+1 == n {
			out[i] = xs[i]
		} else {
			out[i] = (xs[i-1] + 2*xs[i] + xs[i+1]) % 1000003
		}
	}
}

func checksum(n int) int64 {
	a := make([]int64, n)
	b := make([]int64, n)
	for i := range a {
		a[i] = (int64(i) * 2654435761) % 1000003
	}
	for k := 0; k < passes; k++ {
		stencil(a, b)
		a, b = b, a
	}
	var s int64
	for _, v := range a {
		s += v
	}
	return s
}

// ---- server-side rendered catalog page, identical to React's renderToString output for
// bench/react/page.tsx. Idiomatic Go without a template engine: strings.Builder + escaping.
var words = [8]string{"Widget", "Gadget", "Gizmo", "Doohickey", "Sprocket", "Flange", "Bracket", "Grommet"}
var adjs = [8]string{"Deluxe", "Basic", "Pro", "Mini", "Ultra", "Classic", "Eco", "Max"}

func escapeInto(b *strings.Builder, s string) {
	for i := 0; i < len(s); i++ {
		switch s[i] {
		case '&':
			b.WriteString("&amp;")
		case '<':
			b.WriteString("&lt;")
		case '>':
			b.WriteString("&gt;")
		case '"':
			b.WriteString("&quot;")
		case '\'':
			b.WriteString("&#x27;")
		default:
			b.WriteByte(s[i])
		}
	}
}

func page(n int) string {
	var b strings.Builder
	b.Grow(200 + n*110)
	b.WriteString("<!DOCTYPE html><html lang=\"en\"><head><title>Catalog</title></head><body><header><h1>Catalog</h1><p>")
	fmt.Fprintf(&b, "%d items", n)
	b.WriteString("</p></header><main><table><thead><tr><th>ID</th><th>Name</th><th>Price</th><th>Stock</th><th>Note</th></tr></thead><tbody>")
	var cents int64
	for i := 0; i < n; i++ {
		dollars := (i * 37) % 1000
		stock := (i * 13) % 50
		cents += int64(dollars)*100 + 99
		if i%2 == 1 {
			b.WriteString("<tr class=\"odd\"><td>")
		} else {
			b.WriteString("<tr class=\"even\"><td>")
		}
		fmt.Fprintf(&b, "%d</td><td>%s %s</td><td>$%d.99</td><td>%d</td><td>", i, words[i%8], adjs[(i*7)%8], dollars, stock)
		if i%5 == 0 {
			escapeInto(&b, "Ben & Jerry's \"Special\" <limited>")
		} else {
			b.WriteByte('-')
		}
		b.WriteString("</td></tr>")
	}
	fmt.Fprintf(&b, "</tbody></table></main><footer>Total: $%d.%02d</footer></body></html>", cents/100, cents%100)
	return b.String()
}

func main() {
	port := os.Args[1]
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		p := r.URL.Path
		switch {
		case r.Method == http.MethodPost && p == "/nbody":
			var req struct {
				N     int `json:"n"`
				Steps int `json:"steps"`
			}
			if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.N < 1 || req.N > 4096 || req.Steps < 0 || req.Steps > 1000 {
				w.Header().Set("Content-Type", "text/plain")
				w.WriteHeader(http.StatusBadRequest)
				w.Write([]byte(`usage: POST /nbody {"n":1..4096,"steps":0..1000}`))
				return
			}
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprintf(w, `{"n":%d,"steps":%d,"energy":%.9f}`, req.N, req.Steps, simulate(req.N, req.Steps))
		case p == "/":
			w.Header().Set("Content-Type", "text/plain")
			w.Write([]byte("Hello, World!"))
		case strings.HasPrefix(p, "/page/"):
			n, err := strconv.Atoi(strings.TrimPrefix(p, "/page/"))
			if err != nil || n < 1 || n > 1000 {
				w.WriteHeader(http.StatusBadRequest)
				w.Write([]byte("usage: /page/N, 1 <= N <= 1000"))
				return
			}
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			w.Write([]byte(page(n)))
		case strings.HasPrefix(p, "/smooth/"):
			n, err := strconv.Atoi(strings.TrimPrefix(p, "/smooth/"))
			if err != nil || n < 1 || n > 1000000 {
				w.Header().Set("Content-Type", "text/plain")
				w.WriteHeader(http.StatusBadRequest)
				w.Write([]byte("usage: /smooth/N, 1 <= N <= 1e6"))
				return
			}
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprintf(w, `{"n":%d,"passes":%d,"checksum":%d}`, n, passes, checksum(n))
		default:
			http.NotFound(w, r)
		}
	})
	fmt.Fprintln(os.Stderr, "go: serving on port", port)
	if err := http.ListenAndServe(":"+port, nil); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
