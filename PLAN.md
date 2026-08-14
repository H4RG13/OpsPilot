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

## Phase 5 — Copilot ✅ merged to `develop`

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

**Resolved in Phase 6:** `create_task`/`list_open_tasks` were deferred here
(see below) and have since been added without touching the Copilot
orchestration, as planned.

---

## Phase 6 — Automation ✅ merged to `develop`

- [x] Tasks module: `GET/POST /tasks`, `PATCH /tasks/{id}`; reads open to
      any org member, writes require `ADMIN`+ (same pattern as
      customers/products/orders)
- [x] Tool registry refactored to a `ToolContext` (organization_id,
      user_id, allow_writes) so a write tool can know who's asking and
      whether it's permitted — the seven Phase 5 read tools were updated
      to the new signature, no behavior change
- [x] `create_task` (write, `requires_write_permission=True`): excluded
      from the tools offered to the model unless
      `POST .../messages` sets `allow_ai_actions: true`; the registry
      re-checks the permission at execution time too, not just at
      schema-advertisement time. Logged via structured application log as
      a stopgap for the Phase 8 `audit_logs` table.
- [x] `list_open_tasks` (read, always available)
- [x] Shared `parse_structured_answer()` extracted out of `CopilotService`
      into `ai/parsing.py` so the weekly-report generator can reuse the
      same structured-JSON contract instead of duplicating it
- [x] `reports` table + `POST /reports/generate` (creates a `queued` row,
      dispatches a Celery task) + `GET /reports` (paginated, tenant-scoped)
- [x] Celery task computes a trailing-7-day revenue/order summary +
      period-over-period comparison via the existing analytics service,
      asks the AI Gateway for insights/recommendations, and stores
      `status: completed` with the results — or `status: failed` +
      `error_message` on any exception, with bounded retry (2 retries,
      30s delay)
- [x] Both Celery-adjacent side effects are behind injectable seams so
      tests never touch a broker or a live LLM: `run_report_generation`
      is a plain function taking `db`/`AIService` as parameters (the
      Celery task is a thin `asyncio.run()` wrapper around it), and `POST
      /reports/generate` depends on an overridable dispatcher function
      rather than calling `.delay()` directly
- [x] Alembic migrations `0005` (tasks) and `0006` (reports)
- [x] 14 new tests (78 total): task CRUD/roles/isolation, create_task
      permission gating (rejected without `allow_writes`, succeeds and
      persists with it) and schema-level exclusion, list_open_tasks
      filtering, report generation success/failure paths against a
      scripted fake provider, reports router with a spy dispatcher

**Known limitation:** no persisted audit log for AI-initiated writes yet
(Phase 8); no `GET /reports/{id}` (matches spec Section 21's API table
exactly — only list + generate are listed).

---

## Phase 7 — Imports ✅ pushed, awaiting merge (`phase/7-imports`)

- [x] `POST /imports/csv` (multipart, `import_type` of `customers` or
      `products`, `ADMIN`+ only) + `GET /imports/{id}`
- [x] Row validation reuses `CustomerCreate`/`ProductCreate` directly —
      import rules can't drift from the regular create-endpoint rules
- [x] Upsert by `email` (customers) / `name` (products), scoped to the
      organization, so re-running a CSV updates rather than duplicates
- [x] Per-row `SAVEPOINT` isolation: one bad row rolls back only its own
      write, not the job or any already-imported rows; up to 50 per-row
      `{row, message}` errors are reported; a CSV missing a required
      column fails the whole job immediately
- [x] Background processing via Celery (`ImportJob` starts `queued`,
      Celery task processes it), mirroring the Phase 6 reports pattern
      exactly: `run_import_job` is a plain function taking `db` directly
      (Celery task is a thin `asyncio.run()` wrapper), and `POST
      /imports/csv` depends on an injectable dispatcher for testability
- [x] File type (`.csv` only) and size (5MB) validation
- [x] Alembic migration `0007`
- [x] 11 new tests (89 total): valid import for both types, an invalid
      row skipped without breaking the rest of the job, duplicate-email
      upsert, malformed-CSV whole-job failure, file validation,
      role/tenant isolation

**Bug caught by actually running the tests, not just writing them:** the
first draft called `db.rollback()` on a per-row validation failure — a
full session rollback, which would have silently wiped out every
already-imported row earlier in the same job (and risked tripping async
SQLAlchemy's lazy-load restrictions on the now-expired `job` object, since
attribute access on an expired instance requires an implicit reload that
async sessions can't do outside an explicit `await`). Replaced with a
`SAVEPOINT` (`db.begin_nested()`) per row, which only undoes that row's
own pending write.

**Deliberate scope cuts, documented in README:** no orders/sales CSV
import (needs cross-referencing existing customers/products by natural
key — real complexity for uncertain demo value); no separate
preview/confirm step from spec Section 17 (validation and import happen
together in one Celery run, with the per-row error report as the
"preview" — a true two-step flow would need server-side staging of parsed
rows, not otherwise needed anywhere in this codebase); CSV headers must
match schema field names exactly, no fuzzy column-mapping UI; raw CSV
text is stored inline in the `import_jobs` row rather than object storage
(spec explicitly calls that out as "optional later," Section 4).

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
| 5 — Copilot | ✅ Merged | `phase/5-copilot` (deleted) |
| 6 — Automation | ✅ Merged | `phase/6-automation` |
| 7 — Imports | 🟡 Pushed, awaiting merge | `phase/7-imports` |
| 8–10 | ⬜ Not started | — |

**Test count:** 89 passing (`cd backend && pytest`) · **Lint:** clean (`ruff check`)

**Branch retention:** as of the Phase 6 → 7 transition, merged branches are
kept (not deleted) per the updated policy in `RULES.md` §9 — branches for
phases 0–5 above were deleted under the old policy before this changed.

**Next action:** merge `phase/7-imports` into `develop` on GitHub, then
start Phase 8 — Quality (rate limiting, audit logs, security hardening,
expanded test coverage).
