// Streams a single chat completion to stdout.
//
// Usage:
//   STAFFKM_BASE_URL=http://localhost STAFFKM_API_KEY=sk_xxx \
//   STAFFKM_WORKSPACE=ws_abc STAFFKM_APP=app_123 \
//     go run ./examples
package main

import (
	"fmt"
	"os"

	"github.com/staffkm-platform/staffkm-sdk-go/staffkm"
)

func main() {
	client, err := staffkm.New(staffkm.Options{
		BaseURL:     os.Getenv("STAFFKM_BASE_URL"),
		APIKey:      os.Getenv("STAFFKM_API_KEY"),
		WorkspaceID: os.Getenv("STAFFKM_WORKSPACE"),
	})
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	app := os.Getenv("STAFFKM_APP")
	err = client.ChatStream(app, "用一句話介紹 staffKM。", "", func(tok string) {
		fmt.Print(tok)
	})
	if err != nil {
		fmt.Fprintln(os.Stderr, "stream error:", err)
		os.Exit(1)
	}
	fmt.Println()
}
