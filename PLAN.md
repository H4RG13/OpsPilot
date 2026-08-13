# Project Plan & Progress — AI Operations Copilot

Tracks phase-by-phase progress against `docs/PROJECT_SPECIFICATION.md`
Section 27. Update this file whenever a phase branch is completed or
merged — check items off in the same commit/PR that finishes them.

Legend: `[x]` done · `[~]` in progress · `[ ]` not started

---

## Phase 0 — Setup ✅ merged to `develop`

- [x] Monorepo structure (`backend/`, `frontend/`, `docs/`)
- [x] Docker Compose: Postgres, Redis, backend, worker, frontend
- [x] FastAPI skeleton: `/health`, request-ID middleware, error handler
- [x] Backend core: `config.py`, `database.py`, `security.py`, `logging.py`
- [x] Shared utils: `exceptions.py`, `pagination.py`, `permissions.py`
- [x] Celery worker scaffold
- [x] Alembic wiring
- [x] React + TypeScript + Vite + Tailwind + TanStack Query scaffold
- [x] `.env.example`, `.gitignore`, `README.md`, `RULES.md`
- [x] pytest scaffold (1 test — health check)

## Phase 1 — Auth ✅ merged to `develop`

- [x] Data model: `User`, `Organization`, `OrganizationMember`, `RefreshToken`
- [x] Cross-dialect `GUID` type (Postgres in prod, SQLite in tests)
- [x] `POST /auth/register` — creates org + OWNER membership, auto-issues tokens
- [x] `POST /auth/login`
- [x] `POST /auth/refresh` — rotation with server-side revocation tracking
- [x] `POST /auth/logout` — refresh-token revocation
- [x] `GET /me`, `GET /organizations/current`
- [x] Role-based authorization: `OWNER` / `ADMIN` / `MEMBER`, `require_role()`
- [x] Tenant context re-verified every request (not just at token issuance)
- [x] Alembic migration `0001`
- [x] 11 tests: register, login, refresh rotation + reuse rejection, logout
      revocation, cross-tenant isolation

**Known limitation:** a user's org context is fixed to their first
membership at token-issue time — no "switch organization" endpoint yet.

## Phase 2 — Core Data ✅ merged to `develop`

- [x] Customers: CRUD, name/email search, status filter, `lifetime_value`
- [x] Products: CRUD, category filter, active/inactive filter
- [x] Orders + order items: creation validates customer/product ids against
      caller's org; `unit_price`/`subtotal`/`total_amount` always computed
      server-side from current product price (client never sends a price)
- [x] Pagination on all list endpoints (`Page`/`PageParams`)
- [x] Reads open to any org member; writes require `ADMIN`+
- [x] Alembic migration `0002`
- [x] 15 tests (26 total): CRUD, filters, pagination, MEMBER-vs-ADMIN
      permission boundaries, cross-tenant isolation

**Known limitation:** no "add member to organization" endpoint yet — an
org only gains members via registration (its creator, as OWNER).

---

## Phase 3 — Analytics ✅ merged to `develop`

- [x] `GET /analytics/overview` — revenue, order count, AOV, customer counts
- [x] `GET /analytics/revenue` — day/week/month trend buckets, date-range filter
- [x] `GET /analytics/products` — top products by revenue, deterministic
      tie-break ordering
- [x] `GET /analytics/customers` — total/new/active/at-risk counts
- [x] `compare_revenue()` service function (period-over-period), built for
      reuse by the Phase 5 AI tool of the same name — no dedicated REST
      endpoint since the spec's API table doesn't list one
- [x] Date-range validation (`start_date` > `end_date` → 422), default to
      trailing 30 days when omitted
- [x] Read-only for any org member (no role restriction)
- [x] 7 tests (33 total): metric correctness against known seeded data,
      cancelled-order exclusion, day-bucketing, tenant isolation, invalid
      range rejection, default-range fallback

**Known limitations:** revenue counts `pending`+`completed` orders only
(documented interpretation, not spec-mandated); "at-risk" customers are
read from the stored `Customer.status` field, not computed from order
recency; the revenue trend endpoint does not backfill zero-revenue date
gaps.

---

## Phase 4 — AI Gateway ✅ merged to `develop`

- [x] `AIProvider` protocol (`generate_text`, `generate_structured`,
      `generate_with_tools`, `generate_vision`)
- [x] `GroqProvider` implementation (OpenAI-compatible wire format over httpx)
- [x] `ModelRouter` — task type → model mapping with two-tier fallback
      chain (Section 26 policy); vision model has no fallback
- [x] `AIService`: retry-then-fallback execution shared by `generate_text`
      and `generate_with_tools`, distinguishing transient (retry/fallback)
      from permanent (fail-fast to next model) provider errors
- [x] `ai_usage` table + `GET /ai/usage` (paginated, `ADMIN`+ only)
- [x] Alembic migration `0003`
- [x] 18 new tests (51 total): `ModelRouter` chain resolution, `AIService`
      retry/fallback/all-models-fail paths against a fake provider,
      `GroqProvider` request/response parsing and error classification via
      `httpx.MockTransport` (no live LLM calls anywhere in the suite),
      usage endpoint auth + tenant scoping

**Known limitations:** per-model costs in `ai/cost.py` are placeholder
estimates, not verified Groq pricing.

**Fixed during implementation:** an empty `ai/models/` package directory
left over from the Phase 0 scaffold silently shadowed the new
`ai/models.py` ORM module (Python resolves a package over a same-named
module) — deleted the stub since it was unused and every other module
keeps its ORM models in `models.py`.

---

## Phase 5 — Copilot ✅ pushed, awaiting merge (`phase/5-copilot`)

- [x] `ai_conversations` / `ai_messages` tables + Alembic migration `0004`
- [x] `POST /ai/conversations`, `GET /ai/conversations` (scoped to the
      caller — chat history is personal), `POST
      /ai/conversations/{id}/messages`
- [x] Tool registry: `get_revenue_summary`, `compare_revenue`,
      `get_order_summary`, `get_top_products`, `get_customer_metrics`,
      `get_at_risk_customers`, `search_customers` — every tool's
      `organization_id` is server-injected, never part of the LLM-facing
      argument schema
- [x] `CopilotService`: up to 3 rounds of tool-calling via
      `AIService.generate_with_tools` before forcing a final answer;
      structured JSON parsed into `StructuredAIAnswer`, with a safe
      fallback (raw text as `answer`, empty lists) if the model's output
      isn't valid JSON matching the schema
- [x] Only the user's question and the final answer are persisted to
      `ai_messages` — intermediate tool-calling turns are ephemeral per
      request (full usage/cost accounting for every underlying call still
      lands in `ai_usage` via `AIService`, regardless)
- [x] 13 new tests (64 total): tool execution + org enforcement + unknown
      tool/invalid-argument errors, `CopilotService` tool-loop/fallback/
      max-rounds paths against a scripted fake provider, conversations
      router end-to-end (create → message → structured response) and
      cross-user/cross-tenant isolation

**Known limitation — deliberate scope cut:** `create_task` and
`list_open_tasks` from the spec's Section 10 tool list are **not**
implemented — they depend on the Tasks module, which is Phase 6
(Automation) per the roadmap. Building Tasks now just to satisfy the tool
list would jump ahead of the phase ordering; the registry is structured so
adding them in Phase 6 won't require touching the Copilot orchestration.

## Phase 6 — Automation `[ ]` not started

- [ ] Tasks module: CRUD, assign, priority, status
- [ ] AI-proposed tasks (via `create_task` tool, requires explicit permission)
- [ ] Celery: weekly business report generation job
- [ ] `GET /reports`, `POST /reports/generate`
- [ ] Tests: task permission boundaries, report job status transitions

## Phase 7 — Imports `[ ]` not started

- [ ] `POST /imports/csv`, `GET /imports/{id}`
- [ ] CSV validation pipeline: type/size → parse → column mapping → row
      validation → preview errors → confirm → batch insert/upsert
- [ ] Background processing via Celery, job status tracking
- [ ] Tests: valid/invalid/duplicate/malformed CSV data

## Phase 8 — Quality `[ ]` not started

- [ ] Rate limiting on AI endpoints
- [ ] Audit log (`audit_logs` table) for security-sensitive + AI write actions
- [ ] Broader security hardening pass
- [ ] Expanded test coverage across all modules

## Phase 9 — Deployment `[ ]` not started

- [ ] Production Docker build
- [ ] GitHub Actions CI (lint/test/build)
- [ ] Environment/secrets handling for a real deployment target
- [ ] Basic monitoring/observability

## Phase 10 — Advanced `[ ]` not started

- [ ] pgvector + document RAG
- [ ] Source citations on AI answers
- [ ] `OpenAIProvider` (Groq stays as the low-cost default)
- [ ] Per-organization model policy configuration
- [ ] AI cost budgets/alerts

---

## Current State Summary

| Phase | Status | Branch |
|---|---|---|
| 0 — Setup | ✅ Merged | `phase/0-setup` (deleted) |
| 1 — Auth | ✅ Merged | `phase/1-auth` (deleted) |
| 2 — Core Data | ✅ Merged | `phase/2-core-data` (deleted) |
| 3 — Analytics | ✅ Merged | `phase/3-analytics` (deleted) |
| 4 — AI Gateway | ✅ Merged | `phase/4-ai-gateway` (deleted) |
| 5 — Copilot | 🟡 Pushed, awaiting merge | `phase/5-copilot` |
| 6–10 | ⬜ Not started | — |

**Test count:** 64 passing (`cd backend && pytest`) · **Lint:** clean (`ruff check`)

**Next action:** merge `phase/5-copilot` into `develop` on GitHub, then
start Phase 6 — Automation (Tasks module — including the deferred
`create_task`/`list_open_tasks` tools — Celery, weekly reports).
