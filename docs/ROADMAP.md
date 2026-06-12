# GenAdvisorIQ — Production Roadmap

Phase 1 (advisor dashboard + AI copilot on live MongoDB data) is complete and merged. This document designs the remaining phases to take GenAdvisorIQ from a working prototype to a scaled, production-ready platform.

Phases are ordered by dependency and risk: security gaps first (they block any real deployment), then the AI and data layers (the product core), then frontend/infra hardening, then scale-out features. Each phase is independently shippable.

---

## Current state and known gaps

| Area | Gap | Risk |
|------|-----|------|
| Security | `POST /api/v1/chat/complete` is an **unauthenticated Claude proxy** — anyone who can reach the server can burn API credits | Critical |
| Security | No auth on any endpoint; no rate limiting; CORS unrestricted | Critical |
| AI | Code default model `claude-3-sonnet-20240229` was **retired Jul 21, 2025** (404s); `.env` overrides it but `CLAUDE_PRICING` has no entry for `claude-sonnet-4-6`, so cost tracking is silently wrong | High |
| AI | Chat responses are blocking (no streaming); full book context rebuilt per request (no prompt caching) | Medium |
| Data | No MongoDB indexes; known data-quality issues (`"Postive"` typo, trailing-space field names, inconsistent collection casing); no historical snapshots so trend charts are disabled | Medium |
| Frontend | Babel-standalone transpiles JSX in the browser; React development builds; no bundling, no tests | Medium |
| Ops | No tests, no CI/CD, no Docker, no metrics/alerting | High |

---

## Phase 2 — Security & Access Control ✅ (shipped)

**Goal:** No endpoint is reachable without an authenticated advisor identity. This is the gate for any non-local deployment.

> **Status:** Implemented. Auth runs against the existing `agents` collection (werkzeug-compatible scrypt hashes preserved); JWT access tokens + rotating httpOnly refresh cookies; all routers protected and advisor-scoped; chat proxy budgeted and rate-limited; security headers + CSP on the SPA; `error_response` now returns real HTTP status codes. Verified: unauthenticated → 401, cross-advisor customer fetch → 404, 6th rapid login → 429, per-advisor budget tracked in `api_usage`.

### Deliverables

1. **Advisor authentication**
   - `advisors` auth collection (email, bcrypt password hash, agent ref) seeded from the existing `agents` collection
   - `POST /api/v1/auth/login` → short-lived JWT access token + httpOnly refresh cookie
   - FastAPI dependency (`get_current_advisor`) applied to every `/api/v1/*` router; the SPA stores nothing sensitive — token in memory, refresh via cookie
2. **Lock down the Claude proxy**
   - `chat/complete` requires auth, enforces a per-advisor daily token budget (tracked in `api_usage`), and caps `max_tokens` server-side
   - Reject requests whose message payload exceeds a size limit
3. **Rate limiting** — `slowapi` (or nginx layer) per-IP and per-advisor limits; stricter bucket on `chat/complete`
4. **Transport & headers** — explicit CORS allowlist, `TrustedHostMiddleware`, security headers (CSP for the SPA, HSTS behind TLS)
5. **Data scoping** — every customer query filters by the authenticated advisor's `AgentId`, so an advisor can only see their own book (this is the foundation Phase 8 multi-tenancy builds on)

### Acceptance criteria
- Unauthenticated requests to any `/api/v1/*` endpoint return 401
- An advisor cannot fetch another advisor's customer by ID (404/403)
- Exceeding the chat token budget returns 429 with a clear message

---

## Phase 3 — AI Layer Upgrade ✅ (shipped)

**Goal:** Modern model, streaming UX, correct cost accounting, and server-side grounding.

> **Status:** Implemented. `POST /api/v1/copilot/ask` streams SSE with a server-built cached book snapshot and advisor-scoped drill-down tools (`get_client_details`, `get_call_history`); pricing table corrected with loud unknown-model warnings; `/api/analyze` uses structured outputs (no parse fallback); per-advisor usage rollups power the new Reports screen. Verified: tool answers grounded in real MongoDB data, cross-book tool requests return "not found", budget shared across chat+copilot, cache writes/reads tracked in cost. Note: prompt-cache hits are best-effort under global inference routing (region-local caches).

### Deliverables

1. **Model migration**
   - Change `config.py` default from retired `claude-3-sonnet-20240229` → `claude-sonnet-4-6` (high-volume production default; `claude-opus-4-8` configurable for premium analysis paths)
   - Add current pricing to `CLAUDE_PRICING`: `claude-sonnet-4-6` $3/$15 per MTok, `claude-opus-4-8` $5/$25, `claude-haiku-4-5` $1/$5; remove retired entries
   - Fail loudly (log warning + flagged metric) when the configured model has no pricing entry instead of silently using a default rate
2. **Streaming chat** — new `POST /api/v1/copilot/ask` streams over SSE using the SDK's `messages.stream()`; the frontend renders tokens incrementally into the existing copilot bubbles (the `Markdown` component re-renders per chunk) and shows tool-activity status events ("Looking up Allen's call history…")
3. **Server-side grounding (snapshot + tools)** — replace browser-built context strings (`askCopilot` reading `window._bookClients`) with a hybrid retrieval design on the backend:
   - **Always-on book snapshot** — one compact line per client (name, id, segment, AUM, health score, last contact, sentiment, next action) serialized server-side from MongoDB and sent as the cached system prompt. Answers broad questions ("who haven't I called in 90 days?") in a single turn with no per-client bloat
   - **Drill-down tools** — Claude requests details only when a question needs them, via advisor-scoped tools: `get_client_details(client_id)` (profile, financials, assets, liabilities, goals, insurance) and `get_call_history(client_id)` (notes, sentiment, purpose). Tools execute server-side with the authenticated advisor's `AgentId` baked into every query — cross-book requests return "not found" no matter what the prompt says
   - The frontend sends only the message history + scope (`book` or `client:{id}`); fetch-on-demand keeps the prompt small while giving the copilot reach into **all** client data, not the top-6 one-liners it had before
4. **Prompt caching** — mark the stable system prompt + book snapshot with `cache_control: {type: "ephemeral"}`; tool definitions share the cached prefix. Copilot conversations hit the cache on every turn (~90% input-cost reduction on repeat turns)
5. **Structured outputs** — replace the fragile "strip markdown fences then `json.loads`" parsing in `query_service.py` with `output_config.format` (JSON schema), eliminating the `parse_error` fallback path
6. **Usage analytics v2** — per-advisor and per-feature (copilot / briefing / summary) token + cost rollups exposed at `GET /api/v1/admin/usage`

### Acceptance criteria
- Copilot responses begin rendering in < 1s (first token)
- `api_usage` cost figures match Anthropic console billing within rounding
- Cache read tokens > 0 on second and later copilot turns in a session
- A question about a client outside the priority top-6 (e.g. insurance coverage, last call notes) is answered from real data via a tool call
- A prompt-injected request for another advisor's client returns "not found" from the tool layer

---

## Phase 4 — Data Layer Hardening

**Goal:** Correct, indexed, versioned data that supports the features the UI had to drop.

### Deliverables

1. **Indexes** — `CustomerId` on Assets/liabilities/insurance/goal/callLogs, `AgentId` on customers, compound index on `api_usage(advisor, date)`; created idempotently at startup
2. **Schema cleanup migration** (one-time script + new write-path validation)
   - Fix sentiment typos (`Postive` → `Positive`), trim trailing-space field names (`"Customer Sentiment "`), normalize insurance status casing
   - Keep the tolerant read-path mappings for one release, then remove them
3. **Historical snapshots** — nightly APScheduler job (the scheduler already exists for summaries) writes per-customer snapshots: `{customer_id, date, total_assets, total_liabilities, net_worth, health_score}` to a `snapshots` collection
   - Re-enables the net-worth trend chart and 30-day-change column removed in Phase 1 — with real data this time
4. **Health score history** — same job records score factors, enabling "score improved 6 pts this month" insights
5. **Pagination & projection** — `advisor/book` supports `limit/offset` and field projection for books larger than ~200 clients; admin customer list paginates
6. **Caching layer** — Redis (or in-process TTL cache initially) for the book endpoint; invalidated by the snapshot job and on writes

### Acceptance criteria
- `advisor/book` p95 latency < 300ms with 1,000 customers (seeded test data)
- Trend charts render from real snapshot data after 7+ days of job runs
- Migration script is idempotent and reversible (writes a backup collection)

---

## Phase 5 — Frontend Production Build

**Goal:** Replace the in-browser Babel prototype setup with a real build, without changing the UX.

### Deliverables

1. **Vite + React build** — move `app/static/*.jsx` into a `frontend/` workspace; output hashed bundles to `app/static/dist/` served by the existing StaticFiles mount. Removes Babel-standalone, React dev builds, and per-page transpilation (current cold load transpiles ~8 JSX files in the browser)
2. **TypeScript migration** — type the API contracts (`BookResponse`, `ClientRecord`, `Persona`) shared with backend Pydantic models
3. **State management** — replace `window._bookClients` / `window._advisorInfo` globals with React context or a small store (TanStack Query fits the fetch-cache-invalidate pattern already in use)
4. **Auth integration** — login screen, token refresh interceptor, logout (pairs with Phase 2)
5. **Quality** — error boundaries around each card, loading skeletons, ESLint/Prettier, Vitest component tests for the data-mapping functions (`buildPersonaFromContext`, formatters), basic a11y pass (keyboard nav, contrast, aria labels)

### Acceptance criteria
- Lighthouse performance score ≥ 90 (currently fails due to Babel transpilation)
- `npm run build` produces a deployable bundle; no `text/babel` scripts remain
- Data-mapping unit tests cover the null-data edge cases fixed in Phase 1 (no expenses, no call logs, "Inforce" status)

---

## Phase 6 — Testing, Observability & Reliability

**Goal:** Know it works, and know when it doesn't.

### Deliverables

1. **Backend test suite** (pytest + httpx + mongomock or a test container)
   - Unit: health-score computation (all factor edge cases), cost calculation, sentiment mapping, date parsing
   - Integration: each endpoint against seeded data; auth/authorization paths; chat proxy budget enforcement (Claude calls mocked)
   - Target: ≥ 80% coverage on `app/services` and `app/api`
2. **Metrics** — Prometheus `/metrics`: request latency histograms per route, Claude token/cost counters, MongoDB query timing, cache hit ratio
3. **Error tracking** — Sentry SDK on backend and frontend, release-tagged
4. **Health endpoints** — split `/healthz` (liveness) from `/readyz` (MongoDB ping + Claude key validity), suitable for orchestrator probes
5. **Structured log hygiene** — request IDs propagated to all logs (partially exists), PII scrubbing in log output, log levels by environment
6. **Resilience** — timeouts + retries with backoff on Claude calls (SDK `max_retries`), circuit breaker on the chat endpoint when Anthropic returns sustained 529s, graceful degradation in the UI (copilot shows "temporarily unavailable" instead of hanging)

### Acceptance criteria
- CI fails on test failure or coverage regression
- A simulated Claude outage degrades only the copilot — the dashboard still loads from MongoDB
- On-call can answer "what's our Claude spend today?" from a dashboard, not a DB query

---

## Phase 7 — Deployment & Scale-Out

**Goal:** Repeatable deploys, horizontal scale, environment separation.

### Deliverables

1. **Containerization** — multi-stage Dockerfile (frontend build stage → Python runtime stage), non-root user, healthcheck; `docker-compose.yml` for local dev (app + MongoDB + Redis)
2. **CI/CD** — GitHub Actions: lint → test → build → image push on merge to `main`; deploy job per environment with manual gate for prod
3. **Environments** — dev / staging / prod with separate MongoDB databases and Claude API keys (staging key with low budget); config via environment, secrets via the platform's secret store (never in image or repo)
4. **Managed MongoDB** — Atlas (or equivalent) with backups, point-in-time restore, network peering; connection pooling tuned for multiple app replicas
5. **Horizontal scaling** — the app is already stateless (sessions in JWT, cache in Redis); run N uvicorn replicas behind a load balancer; APScheduler jobs moved to a single dedicated worker (or a distributed lock) so snapshots don't run N times
6. **Load testing** — Locust/k6 profile: 100 concurrent advisors browsing + 20 concurrent copilot streams; establish capacity baseline and autoscaling thresholds

### Acceptance criteria
- A commit to `main` reaches staging with zero manual steps
- Killing one app replica causes no user-visible errors
- Documented restore procedure tested against a backup

---

## Phase 8 — Multi-Tenancy, Compliance & Advanced AI

**Goal:** Multiple firms, regulatory readiness, and AI features beyond chat.

### Deliverables

1. **Multi-tenancy** — `firms` collection; advisors belong to firms; all data partitioned by firm ID (building on Phase 2 advisor scoping); per-firm Claude budgets and model tiers
2. **RBAC** — roles: advisor, team lead (sees team books), firm admin (manages users/budgets), platform admin
3. **Compliance for financial data**
   - Field-level encryption for PII at rest; TLS everywhere
   - Immutable audit log: who viewed/exported which client data, every AI prompt + response retained per retention policy
   - Data subject rights: export and delete a customer's data end-to-end
   - AI disclosure: every AI-generated surface labeled (already done in UI) and logged with model + version for explainability
4. **Advanced AI features**
   - **Scheduled briefings** — nightly batch job (Batches API, 50% cost) pre-generates morning briefings and client summaries instead of generating on page load
   - **RAG over call logs** — embed call notes; copilot cites specific past conversations ("In your March call, Susan mentioned…")
   - **Meeting prep packs** — one-click document (goals delta, score trend, talking points) generated server-side
   - **Evals** — golden-set regression suite for copilot answers (grounding accuracy, no-hallucinated-numbers checks) run in CI before any prompt or model change ships
5. **Client portal (optional product expansion)** — read-only customer-facing view with its own auth realm; the `client.jsx` view from the original design bundle becomes relevant here

### Acceptance criteria
- Two firms on one deployment cannot see each other's data (verified by integration tests)
- Every AI response is traceable to its prompt, model, and source data
- Prompt changes that regress the eval suite are blocked in CI

---

## Sequencing summary

```
Phase 2  Security & Access Control      ← blocks any real deployment
Phase 3  AI Layer Upgrade               ← model retired; cost tracking wrong today
Phase 4  Data Layer Hardening           ← unlocks trend features; needs Phase 3's scheduler patterns
Phase 5  Frontend Production Build      ← parallelizable with Phase 4
Phase 6  Testing & Observability        ← should start alongside 2–5, completes here
Phase 7  Deployment & Scale-Out         ← needs 2 (auth), 5 (build), 6 (probes/CI)
Phase 8  Multi-Tenancy & Advanced AI    ← needs everything above
```

Phases 2 and 3 are the immediate priorities: Phase 2 because the open Claude proxy is a cost/abuse liability the moment the server is reachable, and Phase 3 because the code's default model no longer exists and cost accounting for the actual model in use is wrong.
