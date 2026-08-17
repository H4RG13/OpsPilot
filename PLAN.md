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

## Phase 7 — Imports ✅ merged to `develop`

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

---

## Phase 8 — Quality ✅ merged to `develop`

- [x] Rate limiting: Redis fixed-window counter behind a `RateLimiter`
      protocol, applied to `POST /ai/conversations/{id}/messages`
      (20/min) and `POST /reports/generate` (5/hour); injectable like
      every other external dependency (`get_ai_service`,
      `get_report_dispatcher`) so the test suite never touches live Redis
- [x] `audit_logs` table + `GET /audit-logs` (paginated, `ADMIN`+ only —
      added beyond spec Section 21's table since an unqueryable audit log
      has no operational value). Four actions logged, each chosen for
      being genuinely security-sensitive or spec-mandated rather than
      instrumenting every write: `auth.register`, `auth.login`,
      `customer.deleted` (the only hard-delete endpoint in the API), and
      `ai.task_created` (replacing the Phase 6 stopgap logger call with a
      real persisted record)
- [x] Consistent error envelope everywhere: FastAPI's default
      `{"detail": [...]}` for validation errors reformatted into
      `{"error": {...}}`; a catch-all handler ensures truly unexpected
      exceptions also return that envelope (`INTERNAL_SERVER_ERROR`, no
      leaked message/traceback) while still logging the real error
      server-side
- [x] Timing-safe login: a dummy bcrypt comparison runs even when the
      submitted email doesn't exist, so response time doesn't leak which
      emails are registered
- [x] Security headers (`X-Content-Type-Options`, `X-Frame-Options`,
      `Referrer-Policy`, `Strict-Transport-Security` in production) via a
      small ASGI middleware
- [x] 16 new tests (105 total): rate limiter logic + 429s on both
      endpoints, audit entries for all four actions (incl. metadata),
      audit-log role/tenant scoping, both reformatted error envelopes,
      security headers

**Bugs caught by actually running the tests, not just writing them:**
(1) `RequestValidationError.errors()` can contain `Decimal` objects
(Pydantic's `gt` constraint context) that plain `json.dumps` chokes on —
the validation-error handler crashed on exactly the input it exists to
handle, fixed with `jsonable_encoder`. (2) The original security-headers/
request-ID middleware used `@app.middleware("http")`, which wraps the app
in Starlette's `BaseHTTPMiddleware` — that runs the downstream app in its
own `anyio` task group, which doesn't reliably propagate exceptions to an
app-level catch-all `Exception` handler (they surfaced as an
`ExceptionGroup`, silently defeating the hardening this phase was
adding). Replaced with a single pure-ASGI middleware class. Also found:
`httpx.ASGITransport` re-raises exceptions into the test after the
response is already sent (mirroring Starlette's `ServerErrorMiddleware`,
which does this deliberately so an ASGI server can still log them) — the
one test verifying the 500-envelope path needs `raise_app_exceptions=
False` on a dedicated client; every other test intentionally keeps the
default so real bugs still surface as loud tracebacks.

**Known limitations, documented rather than silently skipped:** audit
logging covers four actions, not every write in the app (a deliberately
narrow, justified set rather than blanket instrumentation); no MFA/
password-reset flow (not in MVP scope); no automated dependency/
vulnerability scanning yet (that's more of a Phase 9 CI concern).

---

## Phase 9 — Deployment ✅ pushed, awaiting merge (`phase/9-deployment`)

No hosting target has been chosen yet, so this phase covers everything
short of an actual live deployment — see README's "Production
Deployment" section for the full writeup.

- [x] GitHub Actions CI (`.github/workflows/ci.yml`): backend job (ruff +
      pytest, no service containers needed — the suite runs entirely
      against in-memory SQLite + injectable fakes) and frontend job
      (ESLint + `tsc` type-check + Vite build)
- [x] `backend/Dockerfile.prod`: multi-stage, no dev/test deps, non-root
      user, no `--reload`, configurable `WEB_CONCURRENCY`, `HEALTHCHECK`
      against `/health`
- [x] `frontend/Dockerfile.prod`: multi-stage, static Vite bundle served
      by `nginx:alpine` (no Node runtime in the final image), proxying
      `/api/` to the backend so the build can use a relative
      `VITE_API_BASE_URL`, with SPA-route fallback to `index.html`
- [x] `docker-compose.prod.yml`: both prod images + Postgres + Redis, no
      source bind-mounts, `APP_ENV=production` (activates the Phase 1
      `SECRET_KEY` strength guard and the HSTS header)
- [x] Environment/secrets documentation in README, generic enough for
      whichever host gets picked later (Render/Fly.io/Railway/a bare VM
      all just need `DATABASE_URL`/`REDIS_URL` pointed at their own
      managed services — `backend`/`worker`/`frontend` don't change)
- [x] Monitoring baseline: `/health` liveness check (already existed),
      `X-Request-Id` on every response, logs tagged with it via the
      existing `ContextVar`. No external APM/error-tracking wired up —
      documented as the natural next step once there's a real target.

**Bug caught by actually building and running the Docker images, not
just writing Dockerfiles:** `Page[Customer]` (and five more `Page[<ORM
model>]` return-type annotations across the other list-endpoint service
functions) crashed the app on import in a clean Python 3.12 container
with `PydanticSchemaGenerationError` — Python evaluates a function's
return-type annotation *eagerly* at definition time unless the module
opts into deferred evaluation, so `Page[Customer]` literally invoked
Pydantic's generic-model machinery against a SQLAlchemy ORM class, which
Pydantic can't build a schema for. This had been silently "working" in
the long-lived local dev venv (Python 3.14) purely by accident of import-
order/caching — it was never guaranteed to work anywhere, and could have
crashed on any fresh boot in any environment, not just Docker. Fixed by
adding `from __future__ import annotations` to the six affected
`service.py` files, deferring all their annotations to strings. This is
exactly the kind of bug a from-scratch container build with a pinned
Python version catches and a long-lived dev environment hides — the same
"don't just write it, build it and run it" discipline applied to every
backend phase's tests, applied here to infrastructure instead: an
unverified Dockerfile is a claim, not a fact, and this one would have
crashed on its very first boot anywhere outside this dev machine.

Also found while documenting: `npm run test` (Vitest) exits non-zero with
"No test files found" — the frontend has no test files yet, since every
phase through Phase 8 stayed backend-focused per the spec's own framing.
README now says so honestly instead of documenting a command that
doesn't actually work; CI runs `lint` + `build` for the frontend, not
`test`.

## Phase 10 — Advanced `[ ]` not started

- [ ] pgvector + document RAG
- [ ] Source citations on AI answers
- [ ] `OpenAIProvider` (Groq stays as the low-cost default)
- [ ] Per-organization model policy configuration
- [ ] AI cost budgets/alerts

---

# Frontend Phases

Phases 0–10 above map to `docs/PROJECT_SPECIFICATION.md` Section 27, which
is entirely backend — the spec explicitly frames the frontend as
"support the backend rather than dominate the project" (Section 2) and
never gives it its own phase breakdown. Through Phase 9 the frontend is
still exactly the Phase 0 scaffold: routing, Tailwind, TanStack Query
wiring, and one placeholder dashboard page — no real screens exist yet.
These phases build the actual UI, numbered as a continuation (11+) so
they're unambiguous in branch names (`phase/11-...`) without colliding
with the backend's 0–10. Each targets a concrete spec section:

## Phase 11 — Frontend Auth & Shell ✅ pushed, awaiting merge (`phase/11-frontend-auth-shell`)

- [x] Login / register pages wired to `POST /auth/login` /
      `POST /auth/register`; register auto-logs-in on success (matches
      the backend's existing "register returns tokens immediately"
      behavior)
- [x] Token storage (`localStorage`) + an axios response interceptor that
      catches a 401, refreshes via `POST /auth/refresh` (de-duplicated
      across concurrent requests with a shared in-flight promise), retries
      the original request once, and force-redirects to `/login` only if
      the refresh itself fails. Auth endpoints (`/auth/login`,
      `/auth/register`, `/auth/refresh`) are explicitly excluded from this
      flow so a wrong-password 401 shows as a normal form error, not a
      forced logout
- [x] Logout clears local tokens and calls `POST /auth/logout`
      (best-effort — the client-side session is already gone either way)
- [x] `ProtectedRoute` layout route: shows a spinner while the initial
      session restore (`GET /me` if a token exists) is in flight, then
      redirects to `/login` (preserving the attempted path) or renders
      the shell
- [x] `AppShell`: sidebar nav linking to every planned section (Phases
      12–16 render as a shared `ComingSoon` placeholder until each is
      built), header showing the current org name (`GET
      /organizations/current`) and the caller's name + role, logout button
- [x] Small hand-rolled UI kit (`Button`, `Input`, `Card`, `Alert`) instead
      of pulling in shadcn/ui from the spec's tech stack — a deliberate,
      documented simplification given how little UI exists so far; worth
      revisiting once there's enough screen surface to justify the setup

**Verified live in a real browser** (Playwright driving the actual dev
server, not just `tsc`/build passing): unauthenticated `/` correctly
redirects to `/login`; login with an existing user lands on the dashboard
with the correct org/role in the header; logout returns to `/login`;
register-with-a-fresh-email auto-logs-in; and — the one that actually
matters — corrupting the stored access token while keeping a valid
refresh token, then reloading, silently recovers via the refresh
interceptor with no visible disruption and no thrown JS errors (the two
401s in the console are just the browser's own network log for the
requests that triggered the refresh, not unhandled exceptions).

**Known limitation:** no frontend tests yet (that's Phase 17, per spec
Section 23's own phasing); `npm run test` still has nothing to run.

## Phase 12 — Frontend Dashboard `[x]` merged

Spec Section 15.

- [x] KPI cards: revenue, orders, active customers, average order value
      (`GET /analytics/overview`), with a 4-card skeleton loading state
      that preserves the grid layout instead of collapsing it
- [x] Revenue trend chart with a day/week/month granularity toggle
      (`GET /analytics/revenue`), Recharts `AreaChart`, empty state when
      there's no data for the selected range
- [x] Top products card (`GET /analytics/products`) — revenue + quantity
      sold per product, ranked
- [x] Customer activity card (`GET /analytics/customers`) — total, new,
      active, at-risk counts, at-risk highlighted when > 0
- [x] Recent orders and recent tasks widgets — last 5 of each, with
      status/priority badges and a "View all" link to the (still
      `ComingSoon`) Phase 13/14 pages
- [x] Shared `QueryState` component so every widget gets consistent
      loading/error/empty handling from one place instead of six
      hand-rolled copies (explicitly required by spec Section 15)

**Verified live in a real browser** (Playwright driving the dev server
with real seeded data — one customer, two products, two orders, one
task): all six widgets render the correct real numbers (revenue
$209.94, 2 orders, 1 active customer, $104.97 AOV, both products and
both orders listed, the seeded task with its priority badge), the
day/week/month toggle switches the chart's active state and re-renders
the trend, and there were zero console errors.

**Bug caught by actually running it:** the dashboard initially kept
rendering the old Phase 11 "coming in Phase 12" placeholder even after
all the new widget files were written — the Vite dev server running
inside the long-lived Docker container needed a restart to pick up the
new route composition cleanly (the bind-mounted source was already
correct; it was a stale dev-server state, not a code bug). Caught only
because the dashboard was checked in an actual browser instead of
trusting `npm run build`/`lint` passing.

**Known limitation:** no frontend tests yet (still Phase 17, per spec
Section 23's own phasing).

## Phase 13 — Frontend Customers & Products `[x]` merged

- [x] Customer list: search + status filter (active/inactive/at_risk) +
      pagination (`GET /customers`)
- [x] Customer create/edit forms in a shared modal, `ADMIN`+ only — the
      "New Customer" button and each row's Edit/Delete actions are
      hidden entirely for `MEMBER`s via a `canWrite(role)` helper that
      mirrors the backend's `require_role(Role.ADMIN)` check
- [x] Customer delete with a confirmation dialog (`ConfirmDialog`,
      built on a small shared `Modal` primitive)
- [x] Product list: category (free-text) + active/inactive filter +
      pagination (`GET /products`)
- [x] Product create/edit forms, same modal + role-gating pattern as
      customers
- [x] New shared primitives added along the way: `Select`, `Modal`,
      `ConfirmDialog`, `Pagination` — reused as-is by both pages, and
      by every future list-with-CRUD screen (Orders, Tasks)

**Verified live in a real browser** (Playwright driving the dev
server): created, searched for, edited, and deleted a test customer;
created and deleted a test product; both pages showed correct
optimistic-free (invalidate-and-refetch) updates after every mutation
and zero console errors. Learned from Phase 12's dev-server bug ahead
of time — the frontend container was restarted before verification
so a stale Vite session couldn't produce a false negative.

**Known limitation:** no frontend tests yet (still Phase 17, per spec
Section 23's own phasing). Table pagination has no page-size selector
(fixed at 20) — not required by the spec, easy to add later if needed.

## Phase 14 — Frontend Orders & Tasks `[ ]` not started

- [ ] Order list with status filter (`GET /orders`)
- [ ] Order detail view showing line items and computed total
- [ ] Create-order flow: pick customer + products/quantities, submit to
      `POST /orders` (client never computes/sends a price — matches the
      backend's server-computed-totals guarantee)
- [ ] Order status update (`PATCH /orders/{id}`)
- [ ] Task list with status/priority filters, create/edit/assign
      (`GET/POST /tasks`, `PATCH /tasks/{id}`)

## Phase 15 — Frontend AI Copilot `[ ]` not started

Spec Section 16.

- [ ] Conversation list + "new conversation" (`GET/POST /ai/conversations`)
- [ ] Chat interface: message list, input box
      (`POST /ai/conversations/{id}/messages`)
- [ ] Structured answer rendering: insights (with severity),
      recommendations, suggested tasks with a "Create task" action per
      the spec's mockup
- [ ] `allow_ai_actions` toggle surfaced in the UI (not silently always
      on or off) so the write-tool permission model from Phase 6 is
      actually usable
- [ ] Rate-limit (429) and upstream-provider-error (502) states handled
      gracefully, not as a raw error screen

## Phase 16 — Frontend Reports & Imports `[ ]` not started

- [ ] Reports list with status (`GET /reports`) + "Generate report"
      action (`POST /reports/generate`)
- [ ] Poll or manually refresh to see a `queued`/`running` report
      transition to `completed`/`failed`
- [ ] CSV import screen: file upload + `import_type` selector
      (`POST /imports/csv`), showing the returned job's
      total/imported/failed counts and per-row errors
      (`GET /imports/{id}`)

## Phase 17 — Frontend Quality `[ ]` not started

Spec Section 23: "Frontend-test critical forms, authentication states,
and Copilot rendering."

- [ ] Vitest + React Testing Library tests for the auth forms and
      protected-route redirect behavior
- [ ] Tests for Copilot message rendering (structured answer, tool
      permission toggle)
- [ ] `npm run test` actually passes and runs in CI (currently a
      documented gap — see Phase 9)
- [ ] Responsive/accessibility pass across the screens built in
      Phases 11–16

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
| 7 — Imports | ✅ Merged | `phase/7-imports` |
| 8 — Quality | ✅ Merged | `phase/8-quality` |
| 9 — Deployment | ✅ Merged | `phase/9-deployment` |
| 10 — Advanced | ⬜ Not started (optional) | — |
| 11 — Frontend Auth & Shell | ✅ Merged | `phase/11-frontend-auth-shell` |
| 12 — Frontend Dashboard | ✅ Merged | `phase/12-frontend-dashboard` |
| 13 — Frontend Customers & Products | 🟡 Pushed, awaiting merge | `phase/13-frontend-customers-products` |
| 14 — Frontend Orders & Tasks | ⬜ Not started | — |
| 15 — Frontend AI Copilot | ⬜ Not started | — |
| 16 — Frontend Reports & Imports | ⬜ Not started | — |
| 17 — Frontend Quality | ⬜ Not started | — |

**Test count:** 105 passing (`cd backend && pytest`) · **Lint:** clean (`ruff check`)

**Branch retention:** as of the Phase 6 → 7 transition, merged branches are
kept (not deleted) per the updated policy in `RULES.md` §9 — branches for
phases 0–5 above were deleted under the old policy before this changed.

**Status:** the core backend MVP (Phases 0–9) is merged and functionally
complete per the spec's Definition of Done (Section 28); Phase 10 is
optional/advanced scope. Phase 11 gave the frontend its first real
screens (auth + shell); Phase 12 added the first real data screen (the
dashboard); Phase 13 adds the first CRUD screens (Customers, Products)
— Phases 14–17 build out the rest, screen by screen, the same
disciplined way the backend was built.

**Next action:** merge `phase/13-frontend-customers-products` into
`develop` on GitHub, then start Phase 14 — Frontend Orders & Tasks.
