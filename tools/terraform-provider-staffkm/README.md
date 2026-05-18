# terraform-provider-staffkm

> v4.4 Theme D — **scaffold only**. Real CRUD lands in v4.5 once the Go SDK ships.

## 為什麼要 Terraform？

`staffkm-cli` 適合 ad-hoc 操作。當你要：

- 在 CI/CD 中**宣告式**管理 N 個 workspace / KB / app
- 跟既有 IaC（VPC、DB、K8s）一起版控
- 想要 plan / apply / drift detection

→ 走 Terraform。

## 範例

```hcl
terraform {
  required_providers {
    staffkm = {
      source  = "staffkm-platform/staffkm"
      version = "0.1.0"
    }
  }
}

provider "staffkm" {
  base_url = "http://localhost"
  token    = var.staffkm_token
}

resource "staffkm_workspace" "demo" {
  name = "demo-workspace"
}

resource "staffkm_kb" "policies" {
  workspace_id = staffkm_workspace.demo.id
  name         = "Company Policies"
}
```

完整版見 `examples/main.tf`。

## 安裝（local dev）

```bash
cd tools/terraform-provider-staffkm
go build -o terraform-provider-staffkm

# Terraform CLI dev override
cat >> ~/.terraformrc <<EOF
provider_installation {
  dev_overrides {
    "staffkm-platform/staffkm" = "$(pwd)"
  }
  direct {}
}
EOF

cd examples
TF_VAR_staffkm_token="$(jq -r .token ~/.staffkm/credentials.json)" terraform plan
```

## 目前狀態

| 元件 | 狀態 |
|---|---|
| Provider schema (`base_url`, `token`) | ✓ |
| `staffkm_workspace` resource | scaffold（Create 回 placeholder id；Read/Update/Delete 空殼） |
| `staffkm_kb` resource | scaffold（同上） |
| 真實 API CRUD | TODO v4.5（待 Go SDK） |
| Data sources | TODO v4.5 |
| Acceptance tests | TODO v4.5 |

## Resources（規劃中）

- `staffkm_workspace`
- `staffkm_kb` + `staffkm_kb_document`
- `staffkm_application`
- `staffkm_user` + `staffkm_user_quota`
- `staffkm_plugin`

## Contributing

1. fork → branch
2. 新 resource：`internal/provider/<name>_resource.go`，註冊到 `provider.go` 的 `Resources()`
3. 加 example 到 `examples/`
4. PR；review 後 merge 到 `main`

License: same as parent monorepo.
