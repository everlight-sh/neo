package main

import (
	"encoding/json"
	"fmt"
	"os"
	"strconv"
)

func main() {
	n, err := strconv.Atoi(os.Args[1])
	if err != nil {
		panic(err)
	}
	var sum int64
	for i := 0; i < n; i++ {
		source := fmt.Sprintf("{\"id\":%d,\"name\":\"café 🚀\",\"active\":true,\"values\":[1,2,3]}", i%1000)
		var value map[string]any
		if err := json.Unmarshal([]byte(source), &value); err != nil {
			panic(err)
		}
		id, ok := value["id"].(float64)
		if !ok {
			panic("id")
		}
		name, ok := value["name"].(string)
		if !ok {
			panic("name")
		}
		values, ok := value["values"].([]any)
		if !ok {
			panic("values")
		}
		sum += int64(id) + int64(len(name)) + int64(len(values)) + 1
	}
	fmt.Println(sum)
}
