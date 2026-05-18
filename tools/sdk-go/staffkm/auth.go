package staffkm

// Login authenticates with username + password and returns the token payload.
func (c *Client) Login(username, password string) (map[string]interface{}, error) {
	req, err := c.newRequest("POST", "/api/v1/auth/login", map[string]string{
		"username": username,
		"password": password,
	})
	if err != nil {
		return nil, err
	}
	var out map[string]interface{}
	if err := c.do(req, &out); err != nil {
		return nil, err
	}
	return out, nil
}

// Refresh exchanges a refresh token for a fresh access token.
func (c *Client) Refresh(refreshToken string) (map[string]interface{}, error) {
	req, err := c.newRequest("POST", "/api/v1/auth/refresh", map[string]string{
		"refresh_token": refreshToken,
	})
	if err != nil {
		return nil, err
	}
	var out map[string]interface{}
	if err := c.do(req, &out); err != nil {
		return nil, err
	}
	return out, nil
}

// Me returns the current user profile.
func (c *Client) Me() (map[string]interface{}, error) {
	req, err := c.newRequest("GET", "/api/v1/auth/me", nil)
	if err != nil {
		return nil, err
	}
	var out map[string]interface{}
	if err := c.do(req, &out); err != nil {
		return nil, err
	}
	return out, nil
}
