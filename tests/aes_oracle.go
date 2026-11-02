package main
import("bufio";"crypto/aes";"crypto/cipher";"encoding/hex";"encoding/json";"os")
type Input struct{Mode int;Key,Nonce,AAD,Data string}
func bytes(s string)[]byte{b,e:=hex.DecodeString(s);if e!=nil{panic(e)};return b}
func main(){scan:=bufio.NewScanner(os.Stdin);scan.Buffer(make([]byte,4096),4<<20);out:=bufio.NewWriter(os.Stdout);defer out.Flush()
 for scan.Scan(){var input Input;if e:=json.Unmarshal(scan.Bytes(),&input);e!=nil{panic(e)};block,e:=aes.NewCipher(bytes(input.Key));if e!=nil{panic(e)};data:=bytes(input.Data);var result []byte
 if input.Mode==0{result=make([]byte,16);block.Encrypt(result,data)}else if input.Mode==3{result=make([]byte,len(data));cipher.NewCTR(block,bytes(input.Nonce)).XORKeyStream(result,data)}else{gcm,e:=cipher.NewGCM(block);if e!=nil{panic(e)};if input.Mode==1{result=gcm.Seal(nil,bytes(input.Nonce),data,bytes(input.AAD))}else{result,e=gcm.Open(nil,bytes(input.Nonce),data,bytes(input.AAD));if e!=nil{result=nil}}};encoded,_:=json.Marshal(hex.EncodeToString(result));out.Write(encoded);out.WriteByte('\n')
 }
}
