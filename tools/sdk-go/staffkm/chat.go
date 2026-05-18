package staffkm

import (
	"bufio"
	"encoding/json"
	"strings"
)

// Chat sends a single (non-streaming) message and returns the parsed response.
func (c *Client) Chat(applicationID, message, conversationID string) (map[string]interface{}, error) {
	body := map[string]interface{}{"user_input": message}
	if conversationID != "" {
		body["conversation_id"] = conversationID
	}
	req, err := c.newRequest("POST", "/api/v1/applications/"+applicationID+"/chat", body)
	if err != nil {
		return nil, err
	}
	var out map[string]interface{}
	if err := c.do(req, &out); err != nil {
		return nil, err
	}
	return out, nil
}

// ChatStream sends a streaming chat request. The handler is invoked once per token.
// The function returns when the upstream emits [DONE] or the stream closes.
func (c *Client) ChatStream(applicationID, message, conversationID string, onToken func(string)) error {
	body := map[string]interface{}{"user_input": message}
	if conversationID != "" {
		body["conversation_id"] = conversationID
	}
	req, err := c.newRequest("POST", "/api/v1/applications/"+applicationID+"/chat", body)
	if err != nil {
		return err
	}
	resp, err := c.doStream(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	scanner := bufio.NewScanner(resp.Body)
	scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || !strings.HasPrefix(line, "data:") {
			continue
		}
		data := strings.TrimSpace(line[5:])
		if data == "[DONE]" {
			return nil
		}
		var parsed map[string]interface{}
		if err := json.Unmarshal([]byte(data), &parsed); err == nil {
			if tok, ok := parsed["token"].(string); ok {
				onToken(tok)
				continue
			}
		}
		onToken(data)
	}
	return scanner.Err()
}
