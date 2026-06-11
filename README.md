# GenAdvisorIQ — AI-Powered Wealth Advisor Platform

A FastAPI backend and React SPA for wealth management advisors. Advisors get a full book-of-business dashboard with AI-generated health scores, prioritised worklists, and an always-on Claude-powered copilot — all grounded in real MongoDB data.

## Features

- **Advisor dashboard** — book-of-business in worklist, table, and card layouts; client detail view with financial cards
- **AI Copilot (grounded, streaming)** — server-side grounding with a cached book snapshot plus drill-down tools: Claude fetches a client's full financials or call history from MongoDB on demand, scoped to the signed-in advisor. Responses stream token-by-token over SSE with live "Looking up…" tool status
- **Health scoring** — 5-factor score (savings rate, debt ratio, goal progress, insurance, emergency fund) computed server-side per client
- **Full MongoDB integration** — customers, assets, liabilities, insurance, goals, call logs; no hardcoded data anywhere in the UI
- **Secure AI proxy** — all Claude calls go through the FastAPI backend; the browser never sees the Anthropic API key
- **Markdown rendering** — all Claude responses render formatted (bold, bullets, headings) in chat bubbles and summary cards
- **Usage & budget dashboard** — Reports screen shows per-advisor tokens, spend, daily budget bar, 14-day trend, and per-feature breakdown
- **Structured outputs** — `/api/analyze` advice is schema-enforced JSON via the Claude structured-outputs API (no fragile response parsing)

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Uvicorn |
| Async DB driver | Motor (MongoDB) |
| AI | Anthropic Claude API (`AsyncAnthropic`) |
| Data validation | Pydantic v2 |
| Frontend | React 18 + Babel standalone (no build step) |
| Serving static files | FastAPI `StaticFiles` + `aiofiles` |

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
Create `.env` at the repo root:
```env
# Required
CLAUDE_API_KEY=your_anthropic_api_key
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=genaibot
JWT_SECRET_KEY=<openssl rand -base64 48>   # sessions reset on restart if omitted

# Optional
CLAUDE_MODEL=claude-sonnet-4-6
CLAUDE_MAX_TOKENS=2000
CLAUDE_TEMPERATURE=0.7
CHAT_DAILY_TOKEN_BUDGET=200000   # per-advisor daily AI token budget
CHAT_MAX_OUTPUT_TOKENS=1500      # server-side cap per chat request
CORS_ALLOWED_ORIGINS=            # comma-separated; empty = same-origin only
ALLOWED_HOSTS=*                  # comma-separated for host header validation
```

### 2b. Create advisor credentials
Authentication runs against the `agents` collection. Set a password for an agent:
```bash
python scripts/set_advisor_password.py <username-or-email> <password>
```

### 3. Run the server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Open the UI
```
http://localhost:8000/ui/GenAdvisorIQ.html
```

Interactive API docs available at `http://localhost:8000/docs`.

## MongoDB Collections

| Collection | Note |
|-----------|------|
| `customers` | Primary client profiles |
| `agents` | Advisor profiles |
| `Assets` | Capital A — client assets |
| `liabilities` | lowercase |
| `insurance` | Insurance policies |
| `goal` | Singular, not `goals` |
| `callLogs` | camelCase |
| `api_usage` | Written by the API on every request |

> Collection names are inconsistent in the source DB — match them exactly when adding queries.

## Architecture

```
POST /api/analyze          →  app/api/routes.py  →  query_service  →  MongoDB + Claude (structured outputs)
GET  /api/v1/advisor/book  →  app/api/v1/advisor.py  (batch-fetch + health score)
POST /api/v1/copilot/ask   →  app/api/v1/copilot.py  (grounded SSE chat + tool loop)
POST /api/v1/chat/complete →  app/api/v1/chat.py     (plain Claude proxy, legacy)
GET  /api/v1/admin/usage   →  app/api/v1/admin.py    (per-advisor usage rollups)
GET  /ui/*                 →  app/static/            (React SPA)
```

### Request flow — `POST /api/v1/copilot/ask` (Phase 3)
The browser sends only the conversation and a scope (`book` or `client:{id}`); all grounding happens server-side:
1. Build a **book snapshot** — one compact line per client (name, id, segment, AUM, health score, last contact, sentiment, next action) — and send it as the system prompt with `cache_control: ephemeral` so later turns hit the prompt cache
2. Claude answers broad questions straight from the snapshot; for specifics it calls **drill-down tools**:
   - `get_client_details(client_id)` — demographics, financials, assets, liabilities, insurance, goals, dependents
   - `get_call_history(client_id, limit)` — call dates, purpose, sentiment, feedback, notes
3. Every tool query is filtered by the authenticated advisor's `AgentId` — a prompt-injected request for another advisor's client returns `not found`
4. Text deltas, tool-status events, and a final usage/budget event stream back over SSE; usage (incl. cache tokens) is logged to `api_usage`

> Prompt-cache hits are best-effort: with global inference routing, consecutive requests can land in different regions, each with its own cache. Cache reads/writes are tracked in the cost calculation either way.

### Request flow — `/api/v1/advisor/book`
1. Fetch all customers from MongoDB
2. Batch-fetch assets, liabilities, insurance, goals, and call logs in parallel (`asyncio.gather` — 5 queries total regardless of client count)
3. Compute a 5-factor health score per client (0–100)
4. Return pre-display fields: `score`, `segment`, `sentiment`, `lastContact`, `opp`, `action`, `hs_factors`

### Request flow — `/ui/GenAdvisorIQ.html`
1. On mount: `GET /api/v1/advisor/book` → populates worklist and KPI tiles
2. On client click: `GET /api/v1/admin/customers/{id}` → builds full persona via `buildPersonaFromContext()`
3. Copilot & briefing: `POST /api/v1/copilot/ask` (SSE) via `window.claude.stream()` — the browser sends only messages + scope; context is built server-side (key never in browser)

### Health score factors

| Factor | Weight | Source |
|--------|--------|--------|
| Savings rate | 0–30 pts | `(income − expenses) / income`; skipped when expenses unknown |
| Debt ratio | 0–25 pts | `1 − (total_liabilities / total_assets)` |
| Goal progress | 0–20 pts | Average `current / target` across all goals |
| Insurance coverage | 0–15 pts | Any policy with status `Active` / `Inforce` / `In Force` |
| Emergency fund | 0–10 pts | Liquid assets ÷ monthly expenses; target = 6 months |

### File structure

```
app/
├── main.py                        # FastAPI app, routers, StaticFiles mount
├── api/
│   ├── routes.py                  # POST /api/analyze (legacy)
│   └── v1/
│       ├── admin.py               # GET /api/v1/admin/customers/{id}, usage, health
│       ├── advisor.py             # GET /api/v1/advisor/book
│       ├── chat.py                # POST /api/v1/chat/complete (plain proxy, legacy)
│       ├── copilot.py             # POST /api/v1/copilot/ask (grounded SSE + tools)
│       └── insights.py           # POST /api/v1/insights/ask
├── services/
│   ├── llm_service.py             # AsyncAnthropic wrapper + pricing/cost metrics
│   ├── copilot_service.py         # Book snapshot, drill-down tools, ownership gate
│   ├── usage_service.py           # Token budget + per-advisor usage rollups
│   ├── query_service.py           # Prompt + JSON schema for /api/analyze
│   ├── database_service.py        # MongoDB queries for /api/analyze context
│   └── summary_service.py         # Background summary refresh scheduler
├── models/
│   ├── api.py                     # success_response / error_response helpers
│   └── database.py                # Pydantic v2 models (PascalCase aliases for MongoDB)
└── core/
    ├── config.py                  # Settings from environment
    └── database.py                # MongoDB singleton (Motor)

app/static/                        # React SPA (no build step)
├── GenAdvisorIQ.html              # Entry point; window.claude polyfill
├── styles.css                     # Design tokens + component styles
├── data.jsx                       # buildPersonaFromContext(), Markdown renderer
├── advisor-data.jsx               # askCopilot() grounded in live book context
├── book.jsx                       # BookView, AdvisorCopilot (streaming), ClientDetail
├── cards.jsx                      # Financial cards (NetWorth, Health, Goals, …)
├── companion.jsx                  # AICompanion, AIBriefing, ExplainModal
├── charts.jsx                     # SVG chart components (AreaTrend, Donut, …)
├── reports.jsx                    # ReportsView — AI usage & budget dashboard
└── tweaks-panel.jsx               # Dev theme / layout tweaks panel
```

## Authentication (Phase 2)

All `/api/v1/*` endpoints require a bearer token except the `auth` routes.

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/auth/login` | `{username, password}` → access token (30 min) + httpOnly refresh cookie (7 days) |
| `POST /api/v1/auth/refresh` | Exchange the refresh cookie for a new access token (rotates the cookie) |
| `POST /api/v1/auth/logout` | Clear the refresh cookie |
| `GET /api/v1/auth/me` | Current advisor profile |

Send the token as `Authorization: Bearer <access_token>`. The SPA handles this automatically (login screen, in-memory token, transparent refresh on 401).

**Data scoping:** every endpoint filters by the authenticated advisor's `AgentId` — an advisor can only see and query their own book. Cross-book customer lookups return 404.

**Guardrails:**
- Copilot & chat proxy: shared per-advisor daily token budget across both endpoints (429 when exhausted), server-side `max_tokens` cap, payload size/turn limits
- Copilot tools only query the authenticated advisor's book — prompt injection cannot reach another book's data
- Rate limits: 120 req/min per IP globally, 5/min on login, 20/min on copilot and chat
- Security headers on all responses; CSP on the SPA; optional `ALLOWED_HOSTS` and CORS allowlist via env

## API Reference

### `GET /api/v1/advisor/book`
Returns the advisor's full book of business with pre-computed display fields.

```json
{
  "advisor": { "name": "Michael Johnson", "initials": "MJ", "title": "Senior Advisor · GEN ADVISOR IQ" },
  "kpis": { "total_aum": 700000, "client_count": 5, "at_risk_count": 4, "goal_count": 3 },
  "clients": [
    {
      "id": "...",
      "name": "Susan Smith",
      "score": 81,
      "aum": 700000,
      "lastContact": 721,
      "sentiment": "warm",
      "segment": "Mass affluent",
      "action": "Urgent: schedule call",
      "hs_factors": [
        { "k": "Savings rate", "v": 100 },
        { "k": "Debt ratio", "v": 77 }
      ]
    }
  ]
}
```

### `POST /api/v1/copilot/ask`
Grounded copilot chat. Streams Server-Sent Events; context (book snapshot + tools) is assembled server-side.

**Request:**
```json
{ "messages": [{ "role": "user", "content": "Does Allen have life insurance?" }], "scope": "book" }
```
`scope` is `"book"` or `"client:<customer_id>"` (adds a client-focus note for the model).

**SSE events:**
```
data: {"type": "text", "text": "Allen currently has"}
data: {"type": "tool", "name": "get_client_details", "label": "Looking up Allen Brown's financial details…"}
data: {"type": "done", "usage": {"input_tokens": 1720, "output_tokens": 233, "cache_read_tokens": 0, "cache_write_tokens": 1253, "cost_usd": 0.0134}, "budget": {"daily_limit": 200000, "used_today": 4521}}
data: {"type": "error", "message": "…"}   // only on failure
```

### `POST /api/v1/chat/complete`
Plain (non-grounded) Claude proxy, kept for one-shot prompts. Never call Anthropic directly from the browser.

**Request:**
```json
{ "messages": [{ "role": "user", "content": "Summarise this client's risk profile." }] }
```

**Response:**
```json
{ "content": "...", "input_tokens": 120, "output_tokens": 85 }
```

### `GET /api/v1/admin/customers/{customer_id}`
Full client context including assets, liabilities, goals, insurance, recent call logs, and a computed financial summary.

### `POST /api/analyze`
Legacy endpoint — personalized financial advice for a single customer question.

### `GET /api/v1/admin/usage`
Per-advisor AI usage rollups (today / all-time totals, per-endpoint breakdown, 14-day daily series, budget status) plus platform-wide totals and the active pricing table. Backs the Reports screen.

## Development Notes

**Pydantic aliases:** MongoDB documents use PascalCase and spaced field names (`FirstName`, `Marital Status`). All models in `app/models/database.py` use `Field(alias="...")` with `populate_by_name=True`.

**Claude model:** Configured via `CLAUDE_MODEL` env var (default `claude-sonnet-4-6`). If you change the model, also add its rates to `CLAUDE_PRICING` in `app/services/llm_service.py` — unknown models log a warning and flag their cost metrics with `"estimated": true` rather than failing silently.

**Frontend globals:** the app shell sets `window._bookClients`, `window._advisorInfo`, `window._bookKpis` after the book fetch (used for offline fallbacks and KPI tiles); `window._aiBudget` is updated from each copilot `done` event. Copilot context itself is built server-side — `askCopilot()` just streams `messages + scope`.

**Markdown in chat:** The `Markdown` component in `data.jsx` uses `marked` (loaded via CDN) to render Claude responses. It is applied to all AI output surfaces — chat bubbles, briefing bands, and summary cards. Worklist snippets strip markdown before truncating to avoid orphaned `**` tokens.

## Requirements

- Python 3.10+
- MongoDB 4.4+
- Anthropic API key
