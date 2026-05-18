package staffkm

// QuotaSummary fetches the current workspace's quota usage.
func (c *Client) QuotaSummary() (*QuotaSummary, error) {
	req, err := c.newRequest("GET", "/api/v1/quota/summary", nil)
	if err != nil {
		return nil, err
	}
	var resp struct {
		Data QuotaSummary `json:"data"`
	}
	if err := c.do(req, &resp); err != nil {
		return nil, err
	}
	return &resp.Data, nil
}

// SetQuota updates monthly caps. Pass nil pointers to leave a field unchanged.
func (c *Client) SetQuota(monthlyTokenCap *int, monthlyCostCapUSD *float64) (*QuotaSummary, error) {
	body := map[string]interface{}{
		"monthly_token_cap":    monthlyTokenCap,
		"monthly_cost_cap_usd": monthlyCostCapUSD,
	}
	req, err := c.newRequest("PUT", "/api/v1/quota", body)
	if err != nil {
		return nil, err
	}
	var resp struct {
		Data QuotaSummary `json:"data"`
	}
	if err := c.do(req, &resp); err != nil {
		return nil, err
	}
	return &resp.Data, nil
}

// ListQuotas (admin) returns all workspace quotas.
func (c *Client) ListQuotas() ([]map[string]interface{}, error) {
	req, err := c.newRequest("GET", "/api/v1/admin/quota", nil)
	if err != nil {
		return nil, err
	}
	var resp struct {
		Data []map[string]interface{} `json:"data"`
	}
	if err := c.do(req, &resp); err != nil {
		return nil, err
	}
	return resp.Data, nil
}
