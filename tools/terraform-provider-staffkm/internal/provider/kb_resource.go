package provider

import (
	"context"

	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/resource/schema"
	"github.com/hashicorp/terraform-plugin-framework/types"
)

// KBResource represents a staffkm_kb (knowledge base) resource.
type KBResource struct{}

type KBModel struct {
	ID          types.String `tfsdk:"id"`
	WorkspaceID types.String `tfsdk:"workspace_id"`
	Name        types.String `tfsdk:"name"`
}

func NewKBResource() resource.Resource {
	return &KBResource{}
}

func (r *KBResource) Metadata(_ context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) {
	resp.TypeName = req.ProviderTypeName + "_kb"
}

func (r *KBResource) Schema(_ context.Context, _ resource.SchemaRequest, resp *resource.SchemaResponse) {
	resp.Schema = schema.Schema{
		Attributes: map[string]schema.Attribute{
			"id":           schema.StringAttribute{Computed: true},
			"workspace_id": schema.StringAttribute{Required: true, Description: "parent workspace id"},
			"name":         schema.StringAttribute{Required: true},
		},
	}
}

// TODO (v4.5): implement CRUD via Go SDK — scaffold returns placeholder ID.

func (r *KBResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan KBModel
	diags := req.Plan.Get(ctx, &plan)
	resp.Diagnostics.Append(diags...)
	if resp.Diagnostics.HasError() {
		return
	}
	plan.ID = types.StringValue("placeholder-kb-id")
	diags = resp.State.Set(ctx, plan)
	resp.Diagnostics.Append(diags...)
}

func (r *KBResource) Read(_ context.Context, _ resource.ReadRequest, _ *resource.ReadResponse) {
	// TODO (v4.5): GET /api/v1/knowledge-bases/{id}
}

func (r *KBResource) Update(_ context.Context, _ resource.UpdateRequest, _ *resource.UpdateResponse) {
	// TODO (v4.5): PATCH /api/v1/knowledge-bases/{id}
}

func (r *KBResource) Delete(_ context.Context, _ resource.DeleteRequest, _ *resource.DeleteResponse) {
	// TODO (v4.5): DELETE /api/v1/knowledge-bases/{id}
}
