# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

The project virtualenv lives at `venv/` — always use `venv/bin/python` / `venv/bin/uvicorn` / `venv/bin/pytest`.

```bash
# Install dependencies (requirements-dev.txt pulls in requirements.txt + pytest/ruff/mypy)
venv/bin/pip install -r requirements-dev.txt

# Run the server (from repo root); frontend at /ui, API docs at /docs
venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Tests
venv/bin/pytest                                            # all
venv/bin/pytest tests/unit/test_llm_pricing.py             # one file
venv/bin/pytest tests/unit/test_llm_pricing.py::test_name  # one test

# Lint / typecheck
venv/bin/ruff check app tests
venv/bin/mypy app

# Create or reset an advisor login (the ONLY way — no self-registration by design)
venv/bin/python scripts/set_advisor_password.py <username-or-email> <new-password>
```

Environment variables go in `.env` at repo root — required: `CLAUDE_API_KEY`, `MONGODB_URL`, `MONGODB_DATABASE`, `JWT_SECRET_KEY`. See README for full list.

## Architecture

FastAPI app serving a React SPA and a set of advisor-scoped JSON/SSE APIs, with service layers between the routes and MongoDB/Claude. All routers mount under `/api/v1`:

| Router (`app/api/v1/`) | Endpoints | Purpose |
|---|---|---|
| `auth.py` | `POST /auth/login`, `/refresh`, `/logout`, `GET /auth/me` | JWT access token (bearer) + httpOnly refresh cookie |
| `advisor.py` | `GET /advisor/book` | Full book of business: per-client health score, AUM, signals |
| `insights.py` | `POST /insights/ask` | Structured financial advice for one owned client |
| `chat.py` | `POST /chat/complete` | Plain Claude proxy for the client-companion chat |
| `copilot.py` | `POST /copilot/ask` (SSE), `GET /copilot/suggestions/{id}` | Grounded copilot with tools + signal-driven suggestion chips |
| `admin.py` | `GET /admin/usage`, `/admin/health`, summary-refresh POSTs | Usage rollups, health check, AI summary regeneration |

**Auth & ownership scoping (non-negotiable):** every data endpoint takes `advisor: Agent = Depends(get_current_advisor)` (`app/core/auth.py`). Customer access is always filtered by the advisor's `AgentId`; cross-book requests return **404 / "not found"** (never 403, to prevent ID enumeration). In the copilot this is `_owned_customer()` in `copilot_service.py` — keep this gate on any new tool or endpoint that touches customer data.

**Request flow for `/api/v1/insights/ask`:**
1. `insights.py` validates the ObjectId, confirms the customer exists *and belongs to the advisor*, then calls `query_service.process_query`.
2. `query_service.py` fetches full customer context (`database_service.get_customer_context`), serializes it (`build_financial_context` → `build_prompt`), and calls Claude with `ADVICE_SCHEMA` enforced via structured outputs — the response is guaranteed JSON, `json.loads`-ed directly.
3. `llm_service.py` wraps `AsyncAnthropic` and appends token/cost metrics using hardcoded rates in `CLAUDE_PRICING`.
4. Usage is logged to the `api_usage` collection in a `finally` block (so it's recorded even on error).

**Request flow for `/api/v1/copilot/ask` (grounded copilot):**
1. `copilot.py` authenticates, validates the payload (`scope` is `book` or `client:<id>`), and checks the per-advisor daily token budget (`usage_service.tokens_used_today`, shared across all AI endpoints via `AI_ENDPOINTS`).
2. `copilot_service.build_system_blocks` builds a one-line-per-client book snapshot plus the `bankProducts` shelf (cached with `cache_control: ephemeral`); for `client:` scope it appends an uncached client-focus block including signals from `signal_service`. Claude drills into specifics via `get_client_details` / `get_call_history` tools.
3. The streaming loop (`MAX_TOOL_ROUNDS=6`) emits SSE events: `{"type": "text"|"tool"|"done"|"error"}`; usage including cache tokens is logged to `api_usage` with `advisor_id`.

**Signal engine (`app/services/signal_service.py`):** rule-based scan of one client's data (upcoming birthday, uncovered medical spend, premium due/overdue, goal shortfall, protection gap, high-APR debt, retirement gap) producing prioritized `{label, ask}` suggestion chips for the copilot UI and a summary line for the client-focus system block. Product recommendations must come only from the `bankProducts` shelf — that rule lives in the copilot system prompt.

**Background jobs:** APScheduler (in `main.py` lifespan) runs `summary_service.refresh_all_summaries` weekly (Mon 02:00) — regenerates the advisor-facing `summary` field on customers whose summary is 3+ months old. Also triggerable via the `/admin` refresh endpoints.

**Middleware stack (`main.py`):** request-ID logging (structlog), security headers + CSP for `/ui`, slowapi rate limiting (per-route `@limiter.limit` on login/chat/copilot), TrustedHost and CORS only when configured in `.env`.

**MongoDB access pattern:** `app/core/database.py` holds a singleton `MongoDB` class initialized at FastAPI startup/shutdown. Most queries go through `DatabaseService` (`app/services/database_service.py`); services may also call `mongodb.get_db()` directly. No ORM — raw Motor async cursor iteration.

**Frontend (`app/static/`):** single-page React app served at `/ui` with **no build step** — JSX files are compiled in-browser by Babel standalone, loaded in dependency order in `GenAdvisorIQ.html` (`tweaks-panel → charts → data → advisor-data → cards → companion → book → reports → inline App`). Components/share state via globals on `window` (e.g. `window.claude.stream` for SSE copilot calls, `window._aiBudget`). New screens need a new `<script type="text/babel">` tag in the HTML, in the right order. The Anthropic API key never reaches the browser — all Claude calls proxy through the FastAPI backend.

## Key conventions

**Pydantic model aliases:** MongoDB documents use PascalCase and spaced field names (`FirstName`, `Marital Status`, `Goal Amount`). Every model in `app/models/database.py` uses `Field(alias="...")` to map these to snake_case Python attributes. Always use `populate_by_name=True` and `model_dump(exclude={"id"})` when passing model data downstream.

**MongoDB collection names are inconsistent** — `Assets` (capital A) but `liabilities`, `customers`, `goal`, `callLogs`, `bankProducts`. Match exactly when adding new queries. (`scripts/migrate_collection_names.py` exists to normalize them but has not been applied — code still uses the old names.)

**Claude model configuration:** `app/core/config.py` reads `CLAUDE_MODEL` from env and defaults to `claude-sonnet-4-6`. When updating the model, also add its rates to `CLAUDE_PRICING` in `llm_service.py` — unknown models log `unknown_model_pricing` and mark cost metrics `"estimated": true`.

**Structured JSON responses:** pass an `output_schema` to `call_llm` for any endpoint that needs guaranteed JSON (`output_config` with a json_schema format; see `ADVICE_SCHEMA` in `query_service.py`). Schemas must mark all properties required and set `additionalProperties: false`. No fence-stripping or `parse_error` fallbacks.

**`PyObjectId`** in `app/models/database.py` is a custom Pydantic v2 validator that accepts both `ObjectId` and `str` inputs. Use it for any new model field that maps to a MongoDB `_id` or reference field.

**Anthropic messages must start with a user turn** — the UI seeds conversations with an assistant greeting, so frontend callers drop leading non-user messages before sending (see `askCopilot` in `advisor-data.jsx`).
