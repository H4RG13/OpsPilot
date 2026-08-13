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

## Phase 2 — Core Data ✅ pushed, awaiting merge (`phase/2-core-data`)

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

## Phase 3 — Analytics `[ ]` not started

- [ ] `GET /analytics/overview` — revenue, order count, customer count, AOV
- [ ] `GET /analytics/revenue` — trend over time, date-range filter
- [ ] `GET /analytics/products` — top products, product performance
- [ ] `GET /analytics/customers` — activity, at-risk detection
- [ ] Date-range comparison support (e.g. this month vs. last month)
- [ ] Tests: metric correctness against known seeded data, tenant isolation

## Phase 4 — AI Gateway `[ ]` not started

- [ ] `AIProvider` protocol (`generate_text`, `generate_structured`,
      `generate_with_tools`, `generate_vision`)
- [ ] `GroqProvider` implementation
- [ ] `ModelRouter` — task type → model mapping (Section 26 policy)
- [ ] Retry + fallback policy, usage/cost/latency logging (`ai_usage` table)
- [ ] Tests with a mocked provider (no live LLM calls in the suite)

## Phase 5 — Copilot `[ ]` not started

- [ ] `ai_conversations` / `ai_messages` tables
- [ ] `POST /ai/conversations`, `GET /ai/conversations`,
      `POST /ai/conversations/{id}/messages`
- [ ] Tool registry: `get_revenue_summary`, `compare_revenue`,
      `get_top_products`, `get_customer_metrics`, `get_at_risk_customers`,
      `get_order_summary`, `search_customers`, `create_task`,
      `list_open_tasks` — every tool enforces caller's `organization_id`
- [ ] Structured response schema (answer/insights/recommendations/
      suggested_tasks)
- [ ] Tests: tool authorization, structured-response schema validation

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
| 2 — Core Data | 🟡 Pushed, awaiting merge | `phase/2-core-data` |
| 3 — Analytics | ⬜ Not started | — |
| 4–10 | ⬜ Not started | — |

**Test count:** 26 passing (`cd backend && pytest`) · **Lint:** clean (`ruff check`)

**Next action:** merge `phase/2-core-data` into `develop` on GitHub, then
start Phase 3 — Analytics.
