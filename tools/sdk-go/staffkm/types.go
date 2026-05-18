package staffkm

import "fmt"

// APIError wraps a non-2xx response.
type APIError struct {
	StatusCode int
	Body       string
}

func (e *APIError) Error() string {
	return fmt.Sprintf("staffkm api error: status=%d body=%s", e.StatusCode, e.Body)
}

// Workspace represents an API workspace.
type Workspace struct {
	ID   string `json:"id"`
	Name string `json:"name"`
	Slug string `json:"slug,omitempty"`
}

// KnowledgeBase is a KB metadata payload.
type KnowledgeBase struct {
	ID          string `json:"id"`
	Name        string `json:"name"`
	Description string `json:"description,omitempty"`
}

// Application is an agent / chat application.
type Application struct {
	ID   string `json:"id"`
	Name string `json:"name"`
	Type string `json:"type,omitempty"`
}

// ChatResponse is a non-streaming chat reply.
type ChatResponse struct {
	Content   string                   `json:"content,omitempty"`
	Citations []map[string]interface{} `json:"citations,omitempty"`
	Usage     map[string]interface{}   `json:"usage,omitempty"`
}

// QuotaSummary is the quota usage snapshot for the current workspace.
type QuotaSummary struct {
	MonthlyTokenCap   *int     `json:"monthly_token_cap,omitempty"`
	MonthlyCostCapUSD *float64 `json:"monthly_cost_cap_usd,omitempty"`
	TokensUsed        int      `json:"tokens_used,omitempty"`
	CostUsedUSD       float64  `json:"cost_used_usd,omitempty"`
}

// envelope is the common `{"data": ...}` wrapper used by some endpoints.
type envelope struct {
	Data interface{} `json:"data"`
}
