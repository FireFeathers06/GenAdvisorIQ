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

Environment variables go in `.env` at repo root — required: `CLAUDE_API_KEY`, `MONGODB_URL`, `MONGODB_DATABASE`. See README for full list.

## Architecture

FastAPI app with three service layers sitting between the HTTP routes and MongoDB/Claude:

```
POST /api/analyze  →  routes.py  →  query_service.process_query()
                                        ├── database_service.get_customer_context()  →  MongoDB (Motor async)
                                        └── llm_service.call_llm()                  →  Anthropic Claude API
```

**Request flow for `/api/analyze`:**
1. `routes.py` validates the customer ObjectId, fetches the customer to confirm existence, then calls `process_query`.
2. `query_service.py` fetches the full customer context from MongoDB, serializes it into a text prompt (`build_financial_context` → `build_prompt`), calls Claude, then parses the JSON response Claude returns. Falls back gracefully if Claude returns non-JSON.
3. `llm_service.py` wraps `AsyncAnthropic`, appends token and cost metrics to every response, and calculates USD costs using hardcoded rates in `CLAUDE_PRICING`.
4. `routes.py` logs every request to the `api_usage` MongoDB collection in a `finally` block (so usage is logged even on error).

**MongoDB access pattern:**  
`app/core/database.py` holds a singleton `MongoDB` class initialized at FastAPI startup/shutdown. All queries go through `DatabaseService` in `app/services/database_service.py`, which calls `mongodb.get_db()` directly. No ORM — raw Motor async cursor iteration.

## Key conventions

**Pydantic model aliases:** MongoDB documents use PascalCase and spaced field names (`FirstName`, `Marital Status`, `Goal Amount`). Every model in `app/models/database.py` uses `Field(alias="...")` to map these to snake_case Python attributes. Always use `populate_by_name=True` and `model_dump(exclude={"id"})` when passing model data downstream.

**MongoDB collection names are inconsistent** — `Assets` (capital A) but `liabilities`, `customers`, `goal`, `callLogs`. Match exactly when adding new queries.

**Claude model configuration:** `app/core/config.py` reads `CLAUDE_MODEL` from env and defaults to `claude-3-sonnet-20240229` (a legacy model). When updating the model, also update `CLAUDE_PRICING` in `llm_service.py` so cost calculations remain accurate.

**Structured JSON responses:** Claude is prompted to return a specific JSON schema. `query_service.py` strips markdown fences before parsing. If `json.loads` fails, a fallback dict with `parse_error` and `raw_response` is returned — downstream callers should check for `parse_error`.

**`PyObjectId`** in `app/models/database.py` is a custom Pydantic v2 validator that accepts both `ObjectId` and `str` inputs. Use it for any new model field that maps to a MongoDB `_id` or reference field.
