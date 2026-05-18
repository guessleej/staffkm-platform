// Package main is the entry point for the staffkm Terraform provider.
//
// v4.4 Theme D — scaffold only. Real CRUD will land in v4.5 after the
// Go SDK ships.
package main

import (
	"context"
	"log"

	"github.com/hashicorp/terraform-plugin-framework/providerserver"

	"github.com/staffkm-platform/terraform-provider-staffkm/internal/provider"
)

func main() {
	err := providerserver.Serve(context.Background(), provider.New, providerserver.ServeOpts{
		Address: "registry.terraform.io/staffkm-platform/staffkm",
	})
	if err != nil {
		log.Fatal(err)
	}
}
