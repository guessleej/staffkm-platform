package provider

import (
	"context"

	"github.com/hashicorp/terraform-plugin-framework/datasource"
	"github.com/hashicorp/terraform-plugin-framework/provider"
	"github.com/hashicorp/terraform-plugin-framework/provider/schema"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/types"
)

// StaffkmProvider is the root provider type.
type StaffkmProvider struct{}

// StaffkmProviderModel maps provider config to Go values.
type StaffkmProviderModel struct {
	BaseURL types.String `tfsdk:"base_url"`
	Token   types.String `tfsdk:"token"`
}

// New is the factory used by main.go and acceptance tests.
func New() provider.Provider {
	return &StaffkmProvider{}
}

func (p *StaffkmProvider) Metadata(_ context.Context, _ provider.MetadataRequest, resp *provider.MetadataResponse) {
	resp.TypeName = "staffkm"
}

func (p *StaffkmProvider) Schema(_ context.Context, _ provider.SchemaRequest, resp *provider.SchemaResponse) {
	resp.Schema = schema.Schema{
		Attributes: map[string]schema.Attribute{
			"base_url": schema.StringAttribute{
				Required:    true,
				Description: "staffKM gateway URL, e.g. https://staffkm.example.com",
			},
			"token": schema.StringAttribute{
				Required:    true,
				Sensitive:   true,
				Description: "JWT access token (obtain via `staffkm-cli login`)",
			},
		},
	}
}

// Configure will, in v4.5, build a typed Go SDK client from the provider model
// and stash it on resp.ResourceData / resp.DataSourceData so resources can use it.
func (p *StaffkmProvider) Configure(_ context.Context, _ provider.ConfigureRequest, _ *provider.ConfigureResponse) {
	// TODO (v4.5): instantiate go-sdk client here
}

func (p *StaffkmProvider) Resources(_ context.Context) []func() resource.Resource {
	return []func() resource.Resource{
		NewWorkspaceResource,
		NewKBResource,
	}
}

func (p *StaffkmProvider) DataSources(_ context.Context) []func() datasource.DataSource {
	return nil
}
