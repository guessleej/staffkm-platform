package staffkm

// Workspaces lists all workspaces visible to the caller.
func (c *Client) Workspaces() ([]Workspace, error) {
	req, err := c.newRequest("GET", "/api/v1/workspaces", nil)
	if err != nil {
		return nil, err
	}
	var resp struct {
		Data []Workspace `json:"data"`
	}
	if err := c.do(req, &resp); err != nil {
		return nil, err
	}
	return resp.Data, nil
}

// CreateWorkspace creates a new workspace.
func (c *Client) CreateWorkspace(name, slug string) (*Workspace, error) {
	body := map[string]string{"name": name}
	if slug != "" {
		body["slug"] = slug
	}
	req, err := c.newRequest("POST", "/api/v1/workspaces", body)
	if err != nil {
		return nil, err
	}
	var resp struct {
		Data Workspace `json:"data"`
	}
	if err := c.do(req, &resp); err != nil {
		return nil, err
	}
	return &resp.Data, nil
}

// GetWorkspace fetches a single workspace by id.
func (c *Client) GetWorkspace(id string) (*Workspace, error) {
	req, err := c.newRequest("GET", "/api/v1/workspaces/"+id, nil)
	if err != nil {
		return nil, err
	}
	var resp struct {
		Data Workspace `json:"data"`
	}
	if err := c.do(req, &resp); err != nil {
		return nil, err
	}
	return &resp.Data, nil
}
