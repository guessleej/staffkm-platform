package provider

import (
	"context"

	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/resource/schema"
	"github.com/hashicorp/terraform-plugin-framework/types"
)

// WorkspaceResource represents a staffkm_workspace resource.
type WorkspaceResource struct{}

type WorkspaceModel struct {
	ID   types.String `tfsdk:"id"`
	Name types.String `tfsdk:"name"`
}

func NewWorkspaceResource() resource.Resource {
	return &WorkspaceResource{}
}

func (r *WorkspaceResource) Metadata(_ context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) {
	resp.TypeName = req.ProviderTypeName + "_workspace"
}

func (r *WorkspaceResource) Schema(_ context.Context, _ resource.SchemaRequest, resp *resource.SchemaResponse) {
	resp.Schema = schema.Schema{
		Attributes: map[string]schema.Attribute{
			"id":   schema.StringAttribute{Computed: true, Description: "workspace UUID"},
			"name": schema.StringAttribute{Required: true, Description: "human-readable workspace name"},
		},
	}
}

// TODO (v4.5): implement Create / Read / Update / Delete via Go SDK.
// Current implementation is scaffold-only — returns a placeholder ID so
// `terraform plan` works for shape testing, but does NOT touch the API.

func (r *WorkspaceResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan WorkspaceModel
	diags := req.Plan.Get(ctx, &plan)
	resp.Diagnostics.Append(diags...)
	if resp.Diagnostics.HasError() {
		return
	}
	plan.ID = types.StringValue("placeholder-ws-id")
	diags = resp.State.Set(ctx, plan)
	resp.Diagnostics.Append(diags...)
}

func (r *WorkspaceResource) Read(_ context.Context, _ resource.ReadRequest, _ *resource.ReadResponse) {
	// TODO (v4.5): GET /api/v1/workspaces/{id}
}

func (r *WorkspaceResource) Update(_ context.Context, _ resource.UpdateRequest, _ *resource.UpdateResponse) {
	// TODO (v4.5): PATCH /api/v1/workspaces/{id}
}

func (r *WorkspaceResource) Delete(_ context.Context, _ resource.DeleteRequest, _ *resource.DeleteResponse) {
	// TODO (v4.5): DELETE /api/v1/workspaces/{id}
}
