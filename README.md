# GenAdvisorIQ — AI-Powered Wealth Advisor Platform

A FastAPI backend and React SPA for wealth management advisors. Advisors get a full book-of-business dashboard with AI-generated health scores, prioritised worklists, and an always-on Claude-powered copilot — all grounded in real MongoDB data.

## Features

- **Advisor dashboard** — book-of-business in worklist, table, and card layouts; client detail view with financial cards
- **AI Copilot** — book-aware and client-aware Claude chat rail; AI briefing band on every view
- **Health scoring** — 5-factor score (savings rate, debt ratio, goal progress, insurance, emergency fund) computed server-side per client
- **Full MongoDB integration** — customers, assets, liabilities, insurance, goals, call logs; no hardcoded data anywhere in the UI
- **Secure AI proxy** — `POST /api/v1/chat/complete` keeps the Anthropic API key server-side; the browser never sees it
- **Markdown rendering** — all Claude responses render formatted (bold, bullets, headings) in chat bubbles and summary cards
- **Usage analytics** — per-request token and cost tracking logged to `api_usage` collection

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

# Optional
CLAUDE_MODEL=claude-3-sonnet-20240229
CLAUDE_MAX_TOKENS=2000
CLAUDE_TEMPERATURE=0.7
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
POST /api/analyze          →  app/api/routes.py  →  query_service  →  MongoDB + Claude
GET  /api/v1/advisor/book  →  app/api/v1/advisor.py  (batch-fetch + health score)
POST /api/v1/chat/complete →  app/api/v1/chat.py     (Claude proxy)
GET  /ui/*                 →  app/static/            (React SPA)
```

### Request flow — `/api/v1/advisor/book`
1. Fetch all customers from MongoDB
2. Batch-fetch assets, liabilities, insurance, goals, and call logs in parallel (`asyncio.gather` — 5 queries total regardless of client count)
3. Compute a 5-factor health score per client (0–100)
4. Return pre-display fields: `score`, `segment`, `sentiment`, `lastContact`, `opp`, `action`, `hs_factors`

### Request flow — `/ui/GenAdvisorIQ.html`
1. On mount: `GET /api/v1/advisor/book` → populates worklist and KPI tiles
2. On client click: `GET /api/v1/admin/customers/{id}` → builds full persona via `buildPersonaFromContext()`
3. All AI calls: `POST /api/v1/chat/complete` → Claude API (key never in browser)

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
│       ├── chat.py                # POST /api/v1/chat/complete (Claude proxy)
│       └── insights.py           # POST /api/v1/insights/ask
├── services/
│   ├── llm_service.py             # AsyncAnthropic wrapper + cost metrics
│   ├── query_service.py           # Prompt building + Claude call for /api/analyze
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
├── book.jsx                       # BookView, AdvisorCopilot, ClientDetail
├── cards.jsx                      # Financial cards (NetWorth, Health, Goals, …)
├── companion.jsx                  # AICompanion, AIBriefing, ExplainModal
├── charts.jsx                     # Recharts wrappers (AreaTrend, etc.)
└── tweaks-panel.jsx               # Dev theme / layout tweaks panel
```

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

### `POST /api/v1/chat/complete`
Proxies a message to Claude. Never call Anthropic directly from the browser.

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
Aggregate token and cost statistics from the `api_usage` collection.

## Development Notes

**Pydantic aliases:** MongoDB documents use PascalCase and spaced field names (`FirstName`, `Marital Status`). All models in `app/models/database.py` use `Field(alias="...")` with `populate_by_name=True`.

**Claude model:** Configured via `CLAUDE_MODEL` env var. If you change the model, also update `CLAUDE_PRICING` in `app/services/llm_service.py` to keep cost calculations accurate.

**Frontend globals:** `book.jsx` sets `window._bookClients`, `window._advisorInfo`, `window._bookKpis` after the book fetch so `askCopilot()` in `advisor-data.jsx` can build a grounded context string without prop-drilling.

**Markdown in chat:** The `Markdown` component in `data.jsx` uses `marked` (loaded via CDN) to render Claude responses. It is applied to all AI output surfaces — chat bubbles, briefing bands, and summary cards. Worklist snippets strip markdown before truncating to avoid orphaned `**` tokens.

## Requirements

- Python 3.10+
- MongoDB 4.4+
- Anthropic API key
