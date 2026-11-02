// Independent standard Go ECDSA used only by native tests (P-256/P-384, any digest).
// Each stdin line is a JSON case; each stdout line is a JSON hex string.
// Mode 0: generate a key pair (result D || uncompressed public point).
// Mode 1: sign Data's digest with private scalar Key (ASN.1 DER signature).
// Mode 2: verify Signature over Data's digest with Public ("yes"/"no").
// Mode 3: public-key validity of Public ("yes"/"no").
// Mode 4: public point for private scalar Key.
// Hash 0 means Data already is the digest; 1/2/3 select SHA-256/384/512.
package main

import (
	"bufio"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/sha256"
	"crypto/sha512"
	"encoding/hex"
	"encoding/json"
	"math/big"
	"os"
)

type Input struct {
	Mode, Curve, Hash             int
	Key, Public, Data, Signature string
}

func decode(s string) []byte { b, e := hex.DecodeString(s); if e != nil { panic(e) }; return b }
func curve(bits int) elliptic.Curve { if bits == 384 { return elliptic.P384() }; return elliptic.P256() }
func digest(hash int, data []byte) []byte {
	switch hash {
	case 1: h := sha256.Sum256(data); return h[:]
	case 2: h := sha512.Sum384(data); return h[:]
	case 3: h := sha512.Sum512(data); return h[:]
	}
	return data
}
func main() {
	scan := bufio.NewScanner(os.Stdin); scan.Buffer(make([]byte, 4096), 16<<20)
	out := bufio.NewWriter(os.Stdout); defer out.Flush()
	for scan.Scan() {
		var input Input
		if e := json.Unmarshal(scan.Bytes(), &input); e != nil { panic(e) }
		c := curve(input.Curve); var result []byte
		switch input.Mode {
		case 0:
			key, e := ecdsa.GenerateKey(c, rand.Reader); if e != nil { panic(e) }
			size := (c.Params().BitSize + 7) / 8
			result = append(key.D.FillBytes(make([]byte, size)), elliptic.Marshal(c, key.X, key.Y)...)
		case 1:
			d := new(big.Int).SetBytes(decode(input.Key)); x, y := c.ScalarBaseMult(decode(input.Key))
			priv := &ecdsa.PrivateKey{PublicKey: ecdsa.PublicKey{Curve: c, X: x, Y: y}, D: d}
			var e error; result, e = ecdsa.SignASN1(rand.Reader, priv, digest(input.Hash, decode(input.Data))); if e != nil { panic(e) }
		case 2:
			x, y := elliptic.Unmarshal(c, decode(input.Public)); result = []byte("no")
			if x != nil && ecdsa.VerifyASN1(&ecdsa.PublicKey{Curve: c, X: x, Y: y}, digest(input.Hash, decode(input.Data)), decode(input.Signature)) { result = []byte("yes") }
		case 3:
			x, _ := elliptic.Unmarshal(c, decode(input.Public)); result = []byte("no"); if x != nil { result = []byte("yes") }
		case 4:
			x, y := c.ScalarBaseMult(decode(input.Key)); result = elliptic.Marshal(c, x, y)
		}
		encoded, _ := json.Marshal(hex.EncodeToString(result)); out.Write(encoded); out.WriteByte('\n')
	}
}
