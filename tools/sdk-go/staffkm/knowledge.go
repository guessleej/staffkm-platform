package staffkm

import (
	"bytes"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
)

// KnowledgeBases lists all KBs in the current workspace.
func (c *Client) KnowledgeBases() ([]KnowledgeBase, error) {
	req, err := c.newRequest("GET", "/api/v1/knowledge", nil)
	if err != nil {
		return nil, err
	}
	var resp struct {
		Data []KnowledgeBase `json:"data"`
	}
	if err := c.do(req, &resp); err != nil {
		return nil, err
	}
	return resp.Data, nil
}

// CreateKnowledgeBase creates a new KB.
func (c *Client) CreateKnowledgeBase(name, description string) (*KnowledgeBase, error) {
	req, err := c.newRequest("POST", "/api/v1/knowledge", map[string]string{
		"name":        name,
		"description": description,
	})
	if err != nil {
		return nil, err
	}
	var resp struct {
		Data KnowledgeBase `json:"data"`
	}
	if err := c.do(req, &resp); err != nil {
		return nil, err
	}
	return &resp.Data, nil
}

// UploadDocument uploads a file into a KB.
func (c *Client) UploadDocument(kbID, filename string, content io.Reader) (map[string]interface{}, error) {
	var buf bytes.Buffer
	w := multipart.NewWriter(&buf)
	part, err := w.CreateFormFile("file", filename)
	if err != nil {
		return nil, fmt.Errorf("create form file: %w", err)
	}
	if _, err := io.Copy(part, content); err != nil {
		return nil, fmt.Errorf("copy: %w", err)
	}
	if err := w.Close(); err != nil {
		return nil, err
	}
	req, err := http.NewRequest("POST", c.BaseURL+"/api/v1/knowledge/"+kbID+"/documents", &buf)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", w.FormDataContentType())
	if c.APIKey != "" {
		req.Header.Set("X-API-Key", c.APIKey)
	}
	if c.Token != "" {
		req.Header.Set("Authorization", "Bearer "+c.Token)
	}
	if c.WorkspaceID != "" {
		req.Header.Set("X-Workspace-ID", c.WorkspaceID)
	}
	var out map[string]interface{}
	if err := c.do(req, &out); err != nil {
		return nil, err
	}
	return out, nil
}

// HitTest runs a hit-test query against a KB and returns the top-k chunks.
func (c *Client) HitTest(kbID, query string, topK int) ([]map[string]interface{}, error) {
	if topK <= 0 {
		topK = 5
	}
	req, err := c.newRequest("POST", "/api/v1/knowledge/"+kbID+"/hit_test", map[string]interface{}{
		"query": query,
		"top_k": topK,
	})
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
