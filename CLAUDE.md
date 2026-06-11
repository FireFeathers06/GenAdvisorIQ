# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server (from repo root)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Interactive API docs
open http://localhost:8000/docs
```

Environment variables go in `.env` at repo root — required: `CLAUDE_API_KEY`, `MONGODB_URL`, `MONGODB_DATABASE`, `JWT_SECRET_KEY`. See README for full list. Use `venv/bin/python` / `venv/bin/uvicorn` / `venv/bin/pytest` — the project virtualenv lives at `venv/`.

## Architecture

FastAPI app with service layers sitting between the HTTP routes and MongoDB/Claude:

```
POST /api/analyze         →  routes.py  →  query_service.process_query()
                                              ├── database_service.get_customer_context()  →  MongoDB (Motor async)
                                              └── llm_service.call_llm()                  →  Anthropic Claude API
POST /api/v1/copilot/ask  →  copilot.py  →  copilot_service (book snapshot + tools)  →  Claude (SSE stream)
```

**Request flow for `/api/analyze`:**
1. `routes.py` validates the customer ObjectId, fetches the customer to confirm existence, then calls `process_query`.
2. `query_service.py` fetches the full customer context from MongoDB, serializes it into a text prompt (`build_financial_context` → `build_prompt`), calls Claude with `ADVICE_SCHEMA` enforced via structured outputs, and `json.loads` the guaranteed-JSON response.
3. `llm_service.py` wraps `AsyncAnthropic`, appends token and cost metrics to every response, and calculates USD costs using hardcoded rates in `CLAUDE_PRICING`.
4. `routes.py` logs every request to the `api_usage` MongoDB collection in a `finally` block (so usage is logged even on error).

**Request flow for `/api/v1/copilot/ask` (grounded copilot):**
1. `copilot.py` authenticates the advisor, validates the payload, and checks the shared daily token budget (`usage_service.tokens_used_today`).
2. `copilot_service.build_system_blocks` builds a one-line-per-client book snapshot (cached with `cache_control: ephemeral`); Claude drills into specifics via `get_client_details` / `get_call_history` tools.
3. Every tool query filters by the advisor's `AgentId` (`_owned_customer`) — cross-book requests return `not found`. Keep this gate on any new tool.
4. Text deltas / tool-status / done events stream back as SSE; usage including cache tokens is logged to `api_usage` with `advisor_id`.

**MongoDB access pattern:**  
`app/core/database.py` holds a singleton `MongoDB` class initialized at FastAPI startup/shutdown. All queries go through `DatabaseService` in `app/services/database_service.py`, which calls `mongodb.get_db()` directly. No ORM — raw Motor async cursor iteration.

## Key conventions

**Pydantic model aliases:** MongoDB documents use PascalCase and spaced field names (`FirstName`, `Marital Status`, `Goal Amount`). Every model in `app/models/database.py` uses `Field(alias="...")` to map these to snake_case Python attributes. Always use `populate_by_name=True` and `model_dump(exclude={"id"})` when passing model data downstream.

**MongoDB collection names are inconsistent** — `Assets` (capital A) but `liabilities`, `customers`, `goal`, `callLogs`. Match exactly when adding new queries.

**Claude model configuration:** `app/core/config.py` reads `CLAUDE_MODEL` from env and defaults to `claude-sonnet-4-6`. When updating the model, also add its rates to `CLAUDE_PRICING` in `llm_service.py` — unknown models log `unknown_model_pricing` and mark cost metrics `"estimated": true`.

**Structured JSON responses:** `/api/analyze` responses are schema-enforced via structured outputs (`output_config` with `ADVICE_SCHEMA` in `query_service.py`) — no fence-stripping or `parse_error` fallback exists anymore. Pass an `output_schema` to `call_llm` for any new endpoint that needs guaranteed JSON.

**`PyObjectId`** in `app/models/database.py` is a custom Pydantic v2 validator that accepts both `ObjectId` and `str` inputs. Use it for any new model field that maps to a MongoDB `_id` or reference field.
