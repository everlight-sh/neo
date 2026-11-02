package main
import("bufio";"fmt";"os";"strconv";"time";"runtime")
var reader=bufio.NewReader(os.Stdin)
func checkpoint(phase string,ns int64,checksum int64,count int){fmt.Printf("%s %d %d %d\n",phase,ns,checksum,count);if _,err:=reader.ReadByte();err!=nil{panic(err)}}
func lookup(m map[string]string,n int,multiplier int64,remaining bool)int64{
 var sum int64
 for i:=0;i<n;i++{v,ok:=m[strconv.Itoa(i)];if remaining&&i%2==0{if ok{panic("present")}}else{if !ok{panic("missing")};parsed,err:=strconv.ParseInt(v,10,64);if err!=nil||parsed!=int64(i)*multiplier{panic("value")};sum+=parsed}}
 return sum
}
func main(){n,err:=strconv.Atoi(os.Args[1]);if err!=nil{panic(err)};reserved:=os.Args[2]!="0"
 start:=time.Now();var m map[string]string;if reserved{m=make(map[string]string,n)}else{m=make(map[string]string)}
 for i:=0;i<n;i++{m[strconv.Itoa(i)]=strconv.Itoa(i*7)};ns:=time.Since(start).Nanoseconds();if len(m)!=n{panic("length")};checkpoint("insert",ns,0,len(m))
 start=time.Now();sum:=lookup(m,n,7,false);checkpoint("lookup",time.Since(start).Nanoseconds(),sum,len(m))
 runtime.GC();checkpoint("steady",0,sum,len(m))
 start=time.Now();for i:=0;i<n;i++{m[strconv.Itoa(i)]=strconv.Itoa(i*11)};checkpoint("update",time.Since(start).Nanoseconds(),0,len(m))
 start=time.Now();sum=lookup(m,n,11,false);checkpoint("lookup_updated",time.Since(start).Nanoseconds(),sum,len(m))
 start=time.Now();for i:=0;i<n;i+=2{delete(m,strconv.Itoa(i))};checkpoint("delete",time.Since(start).Nanoseconds(),0,len(m))
 start=time.Now();sum=lookup(m,n,11,true);checkpoint("lookup_remaining",time.Since(start).Nanoseconds(),sum,len(m));runtime.KeepAlive(m)
}
