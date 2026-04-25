# API Routes Reference

Base URL: `http://localhost:8000`

---

## Auth

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/auth/signup` | Register a new user. Pass `invite_code` matching `ADMIN_SIGNUP_CODE` env var to get Admin role. |
| `POST` | `/auth/login` | Login with `username` + `password` (form-data). Returns `access_token`. |
| `GET` | `/auth/github/login` | Redirect to GitHub OAuth flow. |
| `GET` | `/auth/github/callback` | GitHub OAuth callback. |
| `GET` | `/auth/google/login` | Redirect to Google OAuth flow. |
| `GET` | `/auth/google/callback` | Google OAuth callback. |
| `GET` | `/auth/reset` | Clear session cookies. |

### POST /auth/signup
```json
{
  "username": "string",
  "email": "string",
  "password": "string (min 8, 1 uppercase, 1 number)",
  "confirm_password": "string",
  "invite_code": "string (optional, grants Admin role)"
}
```

### POST /auth/login  
Form-data fields: `username`, `password`  
Returns: `{ "access_token": "...", "token_type": "bearer", "user": { "username", "role" } }`

---

## User — Self-service

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/user/get/{search_term}` | Get a user by `user_id`, `username`, or `email`. |
| `PATCH` | `/api/user/update/{search_term}` | Update own `username`, `email`, or `password`. |
| `POST` | `/api/user/set-initial-password/{user_id}` | Set a password for OAuth users who signed in via GitHub/Google. |
| `DELETE` | `/api/user/delete/{search_term}` | Soft-deactivate own account. |

### PATCH /api/user/update/{search_term}
```json
{
  "username": "string (optional)",
  "email": "string (optional)",
  "password": "string (optional, min 8, 1 uppercase, 1 number)"
}
```

### POST /api/user/set-initial-password/{user_id}
```json
{ "new_password": "string (min 8)" }
```

---

## Admin — Users

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/admin/users` | List all users with full profile. |
| `PATCH` | `/api/admin/users/{user_id}` | Update any user field (role, token limits, status, etc). |
| `POST` | `/api/admin/users/create` | Create a new user account directly (no invite code needed). |

### PATCH /api/admin/users/{user_id}
All fields optional. Updatable: `username`, `email`, `password`, `role` (`Admin`\|`Client`), `avatar_url`, `status`, `token_used`, `max_token`.
```json
{
  "max_token": 50000,
  "role": "Admin",
  "status": "online"
}
```

### POST /api/admin/users/create
```json
{
  "username": "string",
  "email": "string",
  "password": "string",
  "role": "Admin | Client"
}
```

---

## Admin — Agents

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/admin/agents` | List all agents (default + custom). |
| `GET` | `/admin/agents/{agent_id}` | Get a single agent's details. |
| `GET` | `/admin/agents/available-models` | List configured models to populate the model dropdown when creating an agent. |
| `POST` | `/admin/agents` | Create a custom agent. |
| `PATCH` | `/admin/agents/{agent_id}` | Update agent settings or assign a model. Default agents cannot be disabled without a model. |
| `DELETE` | `/admin/agents/{agent_id}` | Delete a custom agent. Default agents cannot be deleted. |
| `POST` | `/admin/agents/{agent_id}/preview` | Create a temporary preview session to test an agent (see Admin — Agent Preview section). |

### POST /admin/agents
```json
{
  "agent_name": "string",
  "task": "string",
  "requirements": "string (system prompt / persona)",
  "max_token": 4096,
  "temperature": 1.0,
  "top_p": 0.5,
  "model_id": "uuid (optional, from /admin/agents/available-models)"
}
```

### PATCH /admin/agents/{agent_id}
All fields optional. Send only what you want to change.
```json
{
  "task": "string",
  "requirements": "string",
  "isdisable": false,
  "max_token": 3000,
  "temperature": 0.8,
  "top_p": 0.9,
  "model_id": "uuid | null"
}
```
> **Note:** Setting `isdisable: false` on a custom agent with no `model_id` returns `400`.

---

## Admin — Models

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/admin/models/choices/providers` | List distinct providers (first dropdown). |
| `GET` | `/admin/models/choices/{provider}` | List model choices for a provider (second dropdown). |
| `GET` | `/admin/models/choices` | List all model choices. |
| `GET` | `/admin/models/gemini/available` | List all models available on the configured Gemini API key. |
| `GET` | `/admin/models` | List all configured models (api_key is masked). |
| `GET` | `/admin/models/{model_id}` | Get a single configured model. |
| `POST` | `/admin/models` | Add a new model configuration with an API key. |
| `PATCH` | `/admin/models/{model_id}` | Update a model configuration. |
| `DELETE` | `/admin/models/{model_id}` | Delete a model. Default model (`ilmu-glm-5.1`) cannot be deleted. Auto-disables any custom agents that used this model. |

### POST /admin/models
```json
{
  "api_key": "string (stored encrypted, shown masked in responses)",
  "model_provider": "string (e.g. ilmu, gemini)",
  "model_choice_id": "uuid (from /admin/models/choices/{provider})",
  "token_unit": 0.001,
  "token_cost": 0.002
}
```

### DELETE /admin/models/{model_id} — Response when agents are affected
```json
{
  "ok": true,
  "deleted": "uuid",
  "warning": "No model detected! Please update model before enabling these agents.",
  "disabled_agents": [{ "agent_id": "...", "agent_name": "..." }]
}
```

---

## Client — Projects

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/client/projects` | Create a new project for a user. |
| `GET` | `/client/projects/user/{user_id}` | List all projects belonging to a user. |
| `GET` | `/client/projects/{project_id}` | Get a single project. |
| `PATCH` | `/client/projects/{project_id}` | Update project details. |
| `DELETE` | `/client/projects/{project_id}` | Delete a project (cascades to all sessions, prompts, and dashboard). |

### POST /client/projects
```json
{
  "user_id": "string",
  "project_name": "string",
  "project_description": "string (optional, max 200 chars)",
  "business_name": "string",
  "business_type": "string",
  "business_context": "string (optional, max 3000 chars)",
  "budget_min": 0,
  "budget_max": 0,
  "goal": "string (optional)"
}
```

### PATCH /client/projects/{project_id}
All fields optional. Send only what changed.
```json
{
  "project_name": "string",
  "business_context": "string",
  "budget_max": 250000,
  "goal": "string"
}
```

---

## Client — Sessions

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/client/sessions` | Open a new session with an agent inside a project. |
| `GET` | `/client/sessions/user/{user_id}` | List all sessions for a user across all projects. |
| `GET` | `/client/sessions/{session_id}` | Get a session with its full message history. |
| `DELETE` | `/client/sessions/{session_id}` | Delete a session and all its messages. |
| `GET` | `/client/sessions/switch/{project_id}/{agent_id}` | List all sessions for a specific project + agent pair (for session switcher UI). Returns newest first. |

### POST /client/sessions
```json
{
  "user_id": "string",
  "project_id": "string (uuid)",
  "agent_id": "string (e.g. AGT0001)",
  "session_name": "string"
}
```

### GET /client/sessions/{session_id} — Response shape
```json
{
  "session": {
    "session_id": "uuid",
    "agent_id": "string",
    "agent_name": "string",
    "project_name": "string",
    "business_name": "string",
    ...
  },
  "history": [
    { "prompt_id": "uuid", "content": "string", "content_type": "prompt | reply", "timestamp": "..." }
  ]
}
```

---

## Client — Chat

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/client/sessions/{session_id}/chat` | Send a message to the agent. Returns the agent's reply. Saves both sides to history. |
| `POST` | `/client/sessions/{session_id}/upload-chat` | Upload a PDF or CSV, extract its content via Gemini, and send it to the agent in one call. |
| `POST` | `/client/sessions/{session_id}/generate` | Generate a downloadable PDF, PPT, or CSV report using the agent's expertise and project context. |

### POST /client/sessions/{session_id}/chat
```json
{ "message": "string" }
```
Returns: `{ "reply": "string" }`

### POST /client/sessions/{session_id}/upload-chat
Form-data (multipart):
- `file`: PDF or CSV file (max 20 MB)
- `message`: string (optional, defaults to *"Analyse this file and provide business insights."*)

Returns: `{ "filename": "...", "extracted_summary": "...", "reply": "..." }`

### POST /client/sessions/{session_id}/generate
```json
{
  "document_type": "pdf | ppt | csv",
  "topic": "string (optional, defaults to the agent's task)"
}
```
Returns: file download (`application/pdf`, `.pptx`, or `text/csv` / `application/zip`).

---

## Client — References

References are scoped to **user + agent** (not per session), so they are shared across all sessions with the same agent.

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/client/references` | Add a reference fact that the agent will draw on in all future sessions. |
| `GET` | `/client/references/user/{user_id}/agent/{agent_id}` | List all references for a user + agent pair. |
| `PATCH` | `/client/references/{reference_id}` | Edit the text of an existing reference. |
| `DELETE` | `/client/references/{reference_id}?user_id={user_id}` | Remove a reference. |

### POST /client/references
```json
{
  "user_id": "string",
  "session_id": "uuid",
  "content": "string (the fact to remember)"
}
```

### PATCH /client/references/{reference_id}
```json
{
  "user_id": "string",
  "content": "string (updated fact)"
}
```

---

## Client — Dashboard

Each project has one dashboard. It is auto-created on first `GET`.

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/client/dashboard/{project_id}` | Get the dashboard for a project including all pinned content. Auto-creates dashboard if it doesn't exist yet. |
| `POST` | `/client/dashboard/{project_id}/add` | Pin an agent reply to the dashboard. |
| `POST` | `/client/dashboard/content/{content_id}/update` | Edit the text of a pinned dashboard item. |
| `POST` | `/client/dashboard/content/{content_id}/reorder` | Move a pinned item to a new position. Automatically shifts neighbours. |
| `POST` | `/client/dashboard/content/{content_id}/delete` | Remove a pinned item from the dashboard. |

### GET /client/dashboard/{project_id} — Response shape
```json
{
  "dashboard_id": "uuid",
  "user_id": "string",
  "project_id": "string",
  "content": [
    {
      "content_id": "uuid",
      "prompt_id": "uuid",
      "dashboard_id": "uuid",
      "content": "string",
      "index": 1
    }
  ]
}
```

### POST /client/dashboard/{project_id}/add
```json
{
  "user_id": "string",
  "prompt_id": "uuid (prompt_id of the agent reply from chat history)",
  "content": "string (the text to pin — can be edited from the original reply)"
}
```

### POST /client/dashboard/content/{content_id}/update
```json
{ "content": "string" }
```

### POST /client/dashboard/content/{content_id}/reorder
```json
{ "new_index": 1 }
```
Moves the item to the new position (1-based). Automatically shifts all neighbours. Safe to specify any index—it will be clamped to valid range.

---

## Client — Run Agent (one-shot, no session)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/client/agents/{agent_id}` | Run an agent with a business context directly without a session. Used for quick one-off analysis. |

### POST /client/agents/{agent_id}
```json
{
  "name": "string (business name)",
  "business_type": "string",
  "expected_costs": 0.0,
  "mode_of_business": "string (optional)",
  "brief_description": "string"
}
```

---

## Client — Purchase

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/client/purchase` | Purchase additional tokens (MVP—no payment gateway). |
| `GET` | `/client/purchase/history/{user_id}` | Get all purchases made by a user. |
| `GET` | `/client/purchase/token-status/{user_id}` | Get current token breakdown: used, available, remaining, refresh time. |

### POST /client/purchase
```json
{
  "user_id": "string",
  "purchase_type": "token"
}
```
Returns: `{ "purchase": {...}, "tokens_added": 5000, "purchased_token_remaining": 7500 }`

### GET /client/purchase/token-status/{user_id} — Response
```json
{
  "user_id": "string",
  "token_used": 1200,
  "max_token": 50000,
  "purchased_token_remaining": 5000,
  "total_available": 55000,
  "tokens_remaining": 53800,
  "token_refresh_at": "2026-04-25T17:09:21Z"
}
```

---

## Admin — Agent Preview (Testing)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/admin/agents/{agent_id}/preview` | Create a temporary preview session to test an agent as a client would. |

### POST /admin/agents/{agent_id}/preview
```json
{
  "user_id": "string (admin user ID)",
  "business_name": "string",
  "business_type": "string",
  "business_context": "string (optional)"
}
```
Returns: `{ "session_id": "uuid", ...session_details }`

---

## Common Response Codes

| Code | Meaning |
|------|---------|
| `200` | OK |
| `201` | Created |
| `400` | Bad request / validation error |
| `403` | Forbidden (e.g. deleting a default agent, enabling agent with no model) |
| `404` | Resource not found |
| `413` | File too large (upload-chat, max 20 MB) |
| `415` | Unsupported file type (only PDF and CSV accepted) |
| `422` | Unprocessable — LLM did not return valid JSON (retry generate) |
| `500` | Internal server error |