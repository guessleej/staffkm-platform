// Package staffkm is the official Go SDK for the staffKM platform.
//
// v4.5 Theme E first cut: covers auth, workspaces, knowledge, applications,
// chat (with SSE streaming), quota, and billing.
package staffkm

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

// Client is the synchronous HTTP client for the staffKM API.
type Client struct {
	BaseURL     string
	APIKey      string
	Token       string
	WorkspaceID string
	httpClient  *http.Client
}

// Options configures a Client.
type Options struct {
	BaseURL     string
	APIKey      string
	Token       string
	WorkspaceID string
	Timeout     time.Duration
}

// New creates a new Client. Either APIKey or Token must be set.
func New(opts Options) (*Client, error) {
	if opts.APIKey == "" && opts.Token == "" {
		return nil, fmt.Errorf("must provide either APIKey or Token")
	}
	timeout := opts.Timeout
	if timeout == 0 {
		timeout = 30 * time.Second
	}
	return &Client{
		BaseURL:     strings.TrimRight(opts.BaseURL, "/"),
		APIKey:      opts.APIKey,
		Token:       opts.Token,
		WorkspaceID: opts.WorkspaceID,
		httpClient:  &http.Client{Timeout: timeout},
	}, nil
}

// newRequest builds an *http.Request with auth headers populated.
// If body is non-nil, it is marshalled to JSON.
func (c *Client) newRequest(method, path string, body interface{}) (*http.Request, error) {
	var rdr io.Reader
	if body != nil {
		buf, err := json.Marshal(body)
		if err != nil {
			return nil, fmt.Errorf("marshal body: %w", err)
		}
		rdr = bytes.NewReader(buf)
	}
	req, err := http.NewRequest(method, c.BaseURL+path, rdr)
	if err != nil {
		return nil, err
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	if c.APIKey != "" {
		req.Header.Set("X-API-Key", c.APIKey)
	}
	if c.Token != "" {
		req.Header.Set("Authorization", "Bearer "+c.Token)
	}
	if c.WorkspaceID != "" {
		req.Header.Set("X-Workspace-ID", c.WorkspaceID)
	}
	return req, nil
}

// do executes a request and unmarshals JSON response into out (if non-nil).
func (c *Client) do(req *http.Request, out interface{}) error {
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode >= 400 {
		return &APIError{StatusCode: resp.StatusCode, Body: string(body)}
	}
	if out == nil || len(body) == 0 {
		return nil
	}
	return json.Unmarshal(body, out)
}

// doStream executes a request and returns the raw response (caller closes Body).
func (c *Client) doStream(req *http.Request) (*http.Response, error) {
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode >= 400 {
		defer resp.Body.Close()
		b, _ := io.ReadAll(resp.Body)
		return nil, &APIError{StatusCode: resp.StatusCode, Body: string(b)}
	}
	return resp, nil
}

func queryString(params map[string]string) string {
	if len(params) == 0 {
		return ""
	}
	q := url.Values{}
	for k, v := range params {
		if v != "" {
			q.Set(k, v)
		}
	}
	if len(q) == 0 {
		return ""
	}
	return "?" + q.Encode()
}
