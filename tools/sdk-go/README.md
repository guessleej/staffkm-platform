# staffkm-sdk-go

Official Go SDK for the staffKM platform.

## Install

```bash
go get github.com/staffkm-platform/staffkm-sdk-go/staffkm
```

(Within this monorepo, the module path resolves locally — no remote fetch
required for development.)

## Quick start

```go
package main

import (
    "fmt"
    "os"

    "github.com/staffkm-platform/staffkm-sdk-go/staffkm"
)

func main() {
    client, err := staffkm.New(staffkm.Options{
        BaseURL:     "https://staffkm.example.com",
        APIKey:      os.Getenv("STAFFKM_API_KEY"),
        WorkspaceID: os.Getenv("STAFFKM_WORKSPACE"),
    })
    if err != nil {
        panic(err)
    }

    // Streaming chat
    err = client.ChatStream("app_123", "hello", "", func(tok string) {
        fmt.Print(tok)
    })
    if err != nil {
        panic(err)
    }
}
```

## Exposed endpoints

| Family | Methods |
|---|---|
| auth | `Login`, `Refresh`, `Me` |
| workspaces | `Workspaces`, `CreateWorkspace`, `GetWorkspace` |
| knowledge | `KnowledgeBases`, `CreateKnowledgeBase`, `UploadDocument`, `HitTest` |
| chat | `Chat`, `ChatStream` |
| quota | `QuotaSummary`, `SetQuota`, `ListQuotas` |
| billing | `BillingUsers`, `BillingUserDetail`, `BillingUsersCSV` |

See `docs/dev/sdks.md` for the cross-language overview.
