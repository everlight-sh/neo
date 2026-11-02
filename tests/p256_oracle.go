// Independent standard Go implementation used only by native tests.
package main
import("bufio";"crypto/ecdh";"crypto/ecdsa";"crypto/elliptic";"crypto/rand";"crypto/sha256";"encoding/hex";"encoding/json";"math/big";"os")
type Input struct{Mode int;Key,Public,Data,Signature string}
func bytes(s string)[]byte{b,e:=hex.DecodeString(s);if e!=nil{panic(e)};return b}
func main(){scan:=bufio.NewScanner(os.Stdin);scan.Buffer(make([]byte,4096),4<<20);out:=bufio.NewWriter(os.Stdout);defer out.Flush()
 for scan.Scan(){var input Input;if e:=json.Unmarshal(scan.Bytes(),&input);e!=nil{panic(e)};var result []byte
 switch input.Mode{
 case 0: x,y:=elliptic.P256().ScalarBaseMult(bytes(input.Key));result=elliptic.Marshal(elliptic.P256(),x,y)
 case 1: d,e:=ecdh.P256().NewPrivateKey(bytes(input.Key));if e!=nil{panic(e)};q,e:=ecdh.P256().NewPublicKey(bytes(input.Public));if e!=nil{panic(e)};result,e=d.ECDH(q);if e!=nil{panic(e)}
 case 2: d:=new(big.Int).SetBytes(bytes(input.Key));x,y:=elliptic.P256().ScalarBaseMult(bytes(input.Key));priv:=&ecdsa.PrivateKey{PublicKey:ecdsa.PublicKey{Curve:elliptic.P256(),X:x,Y:y},D:d};h:=sha256.Sum256(bytes(input.Data));var e error;result,e=ecdsa.SignASN1(rand.Reader,priv,h[:]);if e!=nil{panic(e)}
 case 3: x,y:=elliptic.Unmarshal(elliptic.P256(),bytes(input.Public));h:=sha256.Sum256(bytes(input.Data));result=[]byte("no");if x!=nil&&ecdsa.VerifyASN1(&ecdsa.PublicKey{Curve:elliptic.P256(),X:x,Y:y},h[:],bytes(input.Signature)){result=[]byte("yes")}
 };encoded,_:=json.Marshal(hex.EncodeToString(result));out.Write(encoded);out.WriteByte('\n')
 }
}
