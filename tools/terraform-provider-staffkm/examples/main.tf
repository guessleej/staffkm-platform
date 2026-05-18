terraform {
  required_providers {
    staffkm = {
      source  = "staffkm-platform/staffkm"
      version = "0.1.0"
    }
  }
}

variable "staffkm_token" {
  type        = string
  sensitive   = true
  description = "JWT access token from `staffkm-cli login`"
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
