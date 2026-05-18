package staffkm

import "io"

// BillingUsers lists per-user usage rollups. Pass an empty month for current.
func (c *Client) BillingUsers(month string) ([]map[string]interface{}, error) {
	req, err := c.newRequest("GET", "/api/v1/billing/users"+queryString(map[string]string{"month": month}), nil)
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

// BillingUserDetail returns a single user's usage detail.
func (c *Client) BillingUserDetail(userID, month string) (map[string]interface{}, error) {
	req, err := c.newRequest("GET", "/api/v1/billing/users/"+userID+queryString(map[string]string{"month": month}), nil)
	if err != nil {
		return nil, err
	}
	var resp struct {
		Data map[string]interface{} `json:"data"`
	}
	if err := c.do(req, &resp); err != nil {
		return nil, err
	}
	return resp.Data, nil
}

// BillingUsersCSV streams the billing CSV export.
func (c *Client) BillingUsersCSV(month string) ([]byte, error) {
	req, err := c.newRequest("GET", "/api/v1/billing/users.csv"+queryString(map[string]string{"month": month}), nil)
	if err != nil {
		return nil, err
	}
	resp, err := c.doStream(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	return io.ReadAll(resp.Body)
}
