# AI Operations Copilot

A multi-tenant business operations SaaS platform where a business imports
operational data, views analytics, asks an AI copilot questions about that
data, receives actionable recommendations, and automates recurring reports.
Built as a portfolio-grade, backend-focused full-stack project demonstrating
Python/FastAPI, PostgreSQL, React/TypeScript, AI model routing and tool
calling, background jobs, security, and testing.

> Status: **Phase 13 — Frontend Customers & Products.** Backend MVP (Phases 0–9)
> is complete; the frontend is being built out phase by phase (see
> `PLAN.md`). See `RULES.md` for the branching
> and release workflow, and
> [`docs/PROJECT_SPECIFICATION.md`](docs/PROJECT_SPECIFICATION.md) for the
> full implementation spec this project follows.

## Core Product Loop

Business data → analytics → AI understanding → recommendation →
task/automation → measurable business action.

## Architecture

```
React + TypeScript  ──HTTPS/JSON──>  FastAPI (API / Auth / Domain Modules)
                                          │
                          ┌───────────────┼────────────────┐
                          ▼                                ▼
                    PostgreSQL                        AI Gateway
                   (business data)                 (routing/providers)
                          │                                │
                          ▼                          Groq-hosted models:
                  Redis + Celery                     GPT OSS 20B / 120B
                (background jobs:                     Qwen 3.6 27B (vision)
              reports / imports)
```

The AI Gateway/Model Router is the key differentiator: business logic never
calls a provider SDK directly. All LLM calls go through an internal
`AIService` → `ModelRouter` → `AIProvider` interface, so providers/models can
be swapped without touching domain code.

## Technology Stack

| Layer         | Technology                          |
|---------------|--------------------------------------|
| Backend       | Python 3.12, FastAPI, Pydantic v2    |
| ORM/Migrations| SQLAlchemy 2.x, Alembic              |
| Database      | PostgreSQL                           |
| Cache/Queue   | Redis, Celery                        |
| Frontend      | React, TypeScript, Vite              |
| Server state  | TanStack Query                       |
| UI            | Tailwind CSS                         |
| Charts        | Recharts                             |
| AI            | Groq (GPT OSS 20B/120B, Qwen 3.6 27B)|
| Testing       | Pytest + HTTPX; Vitest                |
| Containers    | Docker + Docker Compose              |

## Repository Structure

```
backend/    FastAPI app, domain modules, AI gateway, Celery workers, tests
frontend/   React + TypeScript + Vite app
docker-compose.yml
.env.example
RULES.md    Branching, commit, and release conventions — read this first
```

## Local Setup

Prerequisites: Docker and Docker Compose.

```bash
cp .env.example .env
# fill in SECRET_KEY and GROQ_API_KEY

docker compose up --build
```

- Backend API: http://localhost:8000 (health check at `/health`)
- Frontend: http://localhost:5173

### Running tests

```bash
# Backend
cd backend
pip install -e ".[dev]"
pytest

# Frontend
cd frontend
npm install
npm run lint    # ESLint
npm run build   # tsc type-check + production build
```

There are no frontend test files yet — `npm run test` (Vitest) exits
non-zero with "No test files found" until the frontend actually has
components with logic worth testing. Per the spec's "backend-focused"
framing (Section 2), every phase so far has stayed on the backend; the
frontend is still the Phase 0 scaffold plus a placeholder dashboard. CI
therefore runs `lint` + `build` for the frontend, not `test` — that will
change once real UI work adds something meaningful to assert against.

## Continuous Integration

Every push and pull request runs [`.github/workflows/ci.yml`](.github/workflows/ci.yml):

- **Backend job:** `ruff check` then `pytest` — no service containers
  needed, since the whole suite runs against an in-memory SQLite database
  and injectable fakes for Redis/Celery/the LLM provider (see Known
  Limitations across every phase above for why that's true by design).
- **Frontend job:** `npm run lint` (ESLint) then `npm run build`
  (type-check + production build).

## Production Deployment

There's no live deployment of this project yet (no hosting target has
been chosen), but everything short of that is in place:

**Production Docker images.** Each service has a hardened, multi-stage
`Dockerfile.prod` alongside its dev `Dockerfile`:

- `backend/Dockerfile.prod` — builds the package without dev/test
  dependencies, runs as a non-root user, no `--reload`, configurable
  worker count via `WEB_CONCURRENCY` (default 2), with a `HEALTHCHECK`
  against `/health`.
- `frontend/Dockerfile.prod` — builds the static Vite bundle, then serves
  it from `nginx:alpine` (no Node runtime in the final image). nginx
  proxies `/api/` to the backend service so the frontend can be built
  with a relative `VITE_API_BASE_URL` (e.g. `/api/v1`) instead of a
  hardcoded backend hostname, and falls back to `index.html` for
  client-side routes.

```bash
# Build and smoke-test either image standalone:
docker build -f backend/Dockerfile.prod -t opspilot-backend backend/
docker build -f frontend/Dockerfile.prod -t opspilot-frontend frontend/
```

**`docker-compose.prod.yml`** wires both together with Postgres and
Redis for a simple single-host deployment — no source bind-mounts, no
dev dependencies, `APP_ENV=production` (which activates the
`SECRET_KEY` strength check in `core/config.py` and the
`Strict-Transport-Security` header):

```bash
cp .env.example .env
# fill in a strong SECRET_KEY (>=32 chars), GROQ_API_KEY, and any other
# real secrets — .env is gitignored and must never be committed

docker compose -f docker-compose.prod.yml up --build -d
```

To use a managed Postgres/Redis instead of the bundled containers (the
usual setup on a real hosting provider), just point `DATABASE_URL`/
`REDIS_URL` in `.env` at them and remove the `db`/`redis` services from
the compose file — `backend`/`worker`/`frontend` don't change either way.

**Secrets.** Never committed; `.env.example` documents every variable
with safe placeholder values. In production, `SECRET_KEY` must be a
real random value (`python -c "import secrets; print(secrets.token_urlsafe(32))"`)
or the app refuses to start (Phase 1's production guard). Whatever host
you deploy to (Render, Fly.io, Railway, a bare VM, etc.), its own secrets
manager or environment-variable UI is where these values belong — not in
version control.

**Monitoring.** `GET /health` is the liveness/readiness check consumed by
both the backend's own `HEALTHCHECK` and (if fronted by a load balancer)
the platform's health probe. Every response carries an `X-Request-Id`
header (generated per-request, or echoed back if the client supplied
one), and every log line is tagged with it via a `ContextVar` — grepping
one request ID across backend logs reconstructs its full request
lifecycle. There's no external APM/metrics export (e.g. Prometheus,
Sentry) wired up yet; that would be the natural next step once there's
an actual deployment target to point it at.

## Multi-Tenancy & Security

Every organization-owned table carries an `organization_id`; every
service/repository query enforces tenant scope derived from the
authenticated membership context, never from client-supplied input.
Role-based permissions (`OWNER`, `ADMIN`, `MEMBER`) gate write actions.
Passwords are hashed with bcrypt; authentication uses short-lived JWT access
tokens with a refresh-token rotation strategy.

## Development Workflow

This repository follows a Git Flow–style branching model
(`main` / `staging` / `develop` / `release/*` / `feature|task|fix/*`) with
Conventional Commits. **See [`RULES.md`](RULES.md) for the full policy** —
read it before starting any task.

## Roadmap

Development proceeds in phases (see the project specification, Section 27):
Setup → Auth → Core Data → Analytics → AI Gateway → Copilot → Automation →
Imports → Quality → Deployment → Advanced (RAG, additional providers).

## Known Limitations (Phase 13)

- Auth is implemented: register (creates an organization + OWNER
  membership), login, JWT access/refresh tokens with rotation-on-refresh,
  logout (refresh-token revocation), `GET /me`, `GET /organizations/current`,
  and role-based (`OWNER`/`ADMIN`/`MEMBER`) authorization.
- A user's organization context is fixed at token-issue time to their first
  membership — there is no "switch organization" endpoint yet for users
  belonging to multiple organizations.
- Core data CRUD is implemented: Customers (search + status filter),
  Products (category + active filter), Orders + order items. All list
  endpoints are paginated. Reads are open to any org member; writes
  (create/update/delete) require the `ADMIN` role or higher — `MEMBER`s are
  read-only by default.
- Order totals and item unit prices are always computed server-side from
  the current product price at order-creation time and are never accepted
  from the client, per the spec's "never let an LLM/client silently alter
  financial values" principle.
- There is no "add member to organization" endpoint yet — an organization
  currently only gains members via registration (its creator, as OWNER).
- Analytics is implemented: `GET /analytics/overview` (revenue, order
  count, AOV, customer counts), `GET /analytics/revenue` (day/week/month
  trend buckets), `GET /analytics/products` (top products by revenue),
  `GET /analytics/customers` (total/new/active/at-risk counts). All accept
  optional `start_date`/`end_date` (default: last 30 days) and are read
  for any org member — no write access is involved.
- Revenue metrics count `pending` + `completed` orders as "booked" revenue
  and exclude `cancelled` orders; this is a documented interpretation, not
  a spec-mandated definition. "At-risk" customers are read directly from
  the `Customer.status` field set by the caller (Phase 2) rather than
  computed from order recency — there's no automatic at-risk detection
  heuristic yet.
- The revenue trend endpoint only returns buckets that contain at least
  one order — it does not backfill zero-revenue gaps in the date range.
- The AI Gateway is implemented: `AIProvider` protocol (`generate_text`,
  `generate_structured`, `generate_with_tools`, `generate_vision`),
  `GroqProvider` (OpenAI-compatible wire format), `ModelRouter` mapping
  task type → model with a two-tier fallback chain (cheap model ↔
  reasoning model; the vision model has no fallback), retry-then-fallback
  execution in `AIService`, and per-call usage/cost/latency logging to
  `ai_usage`. `GET /ai/usage` (paginated, `ADMIN`+ only) exposes it.
- Estimated per-model costs in `ai/cost.py` are placeholder figures for
  relative tracking, not verified current Groq pricing — the spec calls
  this out explicitly (Section 33) as something to confirm before relying
  on it for real budget decisions.
- The Copilot is implemented: `POST /ai/conversations`, `GET
  /ai/conversations` (scoped to the caller — chat history is personal,
  not shared org-wide), `POST /ai/conversations/{id}/messages`. A question
  runs through `AIService.generate_with_tools`, executing up to 3 rounds
  of tool calls before forcing a final answer, and returns the structured
  `{answer, insights, recommendations, suggested_tasks}` shape from spec
  Section 12. If the model's final response isn't valid JSON matching that
  schema, the raw text is returned as `answer` with empty lists rather
  than failing the request — the frontend never has to parse unpredictable
  free-form output.
- Nine tools are registered, seven read-only (`get_revenue_summary`,
  `compare_revenue`, `get_order_summary`, `get_top_products`,
  `get_customer_metrics`, `get_at_risk_customers`, `search_customers`,
  `list_open_tasks`) plus one write tool (`create_task`). Every tool's
  `organization_id` is injected by the server from the authenticated
  context — never part of the tool's argument schema.
- Only the user's question and the model's final answer are persisted to
  `ai_messages`; intermediate tool-call/tool-result turns are ephemeral
  within a single request. Full usage/cost/latency accounting for every
  underlying model call (including intermediate tool-calling rounds)
  still lands in `ai_usage` regardless, via `AIService`.
- Tested entirely against a scripted fake provider — no live LLM calls in
  the suite, consistent with every prior phase.
- Tasks module is implemented: `GET/POST /tasks`, `PATCH /tasks/{id}`,
  with the same read-open / `ADMIN`+-write pattern as other domain
  modules. `create_task` is a write tool: it's excluded from the tools
  offered to the model entirely unless the request sets
  `allow_ai_actions: true` on `POST /ai/conversations/{id}/messages`
  ("safe by default" — spec Section 10), and the registry double-checks
  the permission again at execution time as defense-in-depth even if a
  provider offered the tool anyway. There's no persisted audit log for
  AI-initiated writes yet (that's the `audit_logs` table in Phase 8) — a
  structured application log line is emitted as a stopgap.
- Weekly report generation is implemented: `POST /reports/generate`
  creates a `queued` `Report` row and enqueues a Celery task; `GET
  /reports` lists them (paginated, tenant-scoped). The Celery task
  computes the trailing-7-day revenue/order summary and a period-over-
  period comparison via the existing analytics service, asks the AI
  Gateway for insights/recommendations using the same structured-JSON
  contract as the Copilot, and stores the result — or `status: failed`
  with `error_message` if anything raises, with bounded retry (2 retries,
  30s delay) at the Celery level.
- The report-generation logic is a plain async function taking a db
  session and an `AIService` as parameters, independent of Celery; the
  Celery task is a thin sync wrapper that supplies both for real via
  `asyncio.run()`. This is what makes it testable without a running
  Redis broker or a live LLM — the test suite calls the function
  directly with a scripted fake provider, the same pattern used
  everywhere else. Likewise, `POST /reports/generate` depends on an
  injectable dispatcher function (real Celery `.delay()` in production,
  a spy in tests) rather than calling Celery directly, mirroring the
  `get_ai_service` dependency-override pattern from Phase 4/5.
- There is no `GET /reports/{id}` — only `GET /reports` (list) and `POST
  /reports/generate`, matching the spec's Section 21 API table exactly.
  Polling a specific report's status means checking the list.
- CSV import is implemented: `POST /imports/csv` (multipart upload,
  `import_type` of `customers` or `products`, `ADMIN`+ only) creates a
  `queued` `ImportJob` and dispatches a Celery task; `GET
  /imports/{id}` returns status/counts/errors. Row validation reuses the
  existing `CustomerCreate`/`ProductCreate` schemas directly rather than
  a separate import-specific schema, so import rules never drift from
  the regular create-endpoint rules.
- Rows upsert rather than insert blindly — by `email` for customers, by
  `name` for products (both scoped to the organization) — so re-running
  the same CSV updates existing records instead of duplicating them.
  Each row runs inside its own `SAVEPOINT`: a bad row rolls back only
  that row's write, not the whole job or any already-imported rows. The
  response reports `total_rows`/`imported_rows`/`failed_rows` plus up to
  50 per-row `{row, message}` errors; a CSV missing a required column
  fails the whole job immediately rather than reporting 200 identical
  per-row errors.
- **Deliberate scope cuts, both disclosed rather than silently skipped:**
  (1) CSV import only supports `customers` and `products` — not
  orders/sales, which the spec also mentions. Importing orders would need
  matching existing customers/products by a natural key and grouping
  CSV rows into orders with line items, real added complexity for
  uncertain portfolio-demo value; this can be added the same way if
  needed later. (2) There is no separate "preview → confirm" step from
  spec Section 17 — validation and import happen together in one Celery
  run, with the full per-row error report as the "preview." A true
  preview/confirm flow would need to stage parsed rows server-side
  between the two requests, which isn't otherwise needed anywhere in
  this codebase. (3) Column headers must match the target schema's field
  names exactly (e.g. `name,email,status,lifetime_value` for customers)
  — there's no fuzzy/interactive column-mapping UI.
- The raw CSV text is stored inline in the `import_jobs` row rather than
  external object storage, since the spec explicitly calls out object
  storage as an "optional later" item (Section 4) and these are small,
  demo-scale files.
- 11 new tests (89 total): valid import for both types, an invalid row
  skipped without breaking the rest of the job, duplicate-email upsert,
  a malformed CSV (missing required columns) failing the whole job,
  file-type/size validation, and router-level role/tenant isolation.
- Rate limiting is implemented on the two AI-consuming endpoints most
  exposed to abuse/cost overrun: `POST /ai/conversations/{id}/messages`
  (20/minute per user) and `POST /reports/generate` (5/hour per user),
  via a Redis fixed-window counter behind a `RateLimiter` protocol —
  exceeding the limit returns 429 `RATE_LIMITED`. Like every external
  dependency in this codebase, it's injectable: tests override
  `get_rate_limiter` with an always-allow fake by default (no live Redis
  in the suite) and a denying fake to verify the 429 path specifically.
- The `audit_logs` table is implemented, logging four actions chosen for
  being genuinely security-sensitive or spec-mandated rather than
  instrumenting every write in the app: `auth.register`, `auth.login`,
  `customer.deleted` (the only hard-delete endpoint in the API), and
  `ai.task_created` (upgrading the Phase 6 stopgap logger call to a real
  persisted record, per spec Section 10's "write tools... should be
  logged"). `GET /audit-logs` (paginated, `ADMIN`+ only) exposes it —
  this endpoint isn't in the spec's Section 21 API table, added because
  an unqueryable audit log has no real operational value.
- Error handling is now consistent everywhere: FastAPI's default
  `{"detail": [...]}` shape for request validation errors is reformatted
  into the app's `{"error": {...}}` envelope, and a catch-all handler
  ensures any genuinely unexpected exception also returns that envelope
  (`INTERNAL_SERVER_ERROR`, no internal message or stack trace) instead
  of leaking framework/library internals — the real exception is still
  logged server-side with its traceback.
- Login runs a bcrypt comparison against a dummy hash even when the
  submitted email doesn't exist, so a nonexistent account doesn't resolve
  measurably faster than a wrong password for a real one (no timing-based
  user enumeration). The error response was already identical either way.
- Security headers (`X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, and `Strict-Transport-Security` in production) are
  added to every response via a small ASGI middleware.
- 16 new tests (105 total): rate limiter fixed-window logic, 429s from
  both rate-limited endpoints, audit log entries for all four actions
  (including metadata on the AI one), `GET /audit-logs` role/tenant
  scoping, the two reformatted error envelopes, and security headers.

**Bugs caught by actually running the tests, not just writing them:**
(1) `RequestValidationError.errors()` can contain `Decimal` objects (e.g.
Pydantic's `gt` constraint context) that plain `json.dumps` can't
serialize — the validation-error handler crashed on exactly the kind of
input it exists to handle gracefully, fixed with `jsonable_encoder`.
(2) The original security-headers/request-ID middleware used FastAPI's
`@app.middleware("http")` decorator, which wraps the app in Starlette's
`BaseHTTPMiddleware` — that implementation runs the downstream app inside
its own `anyio` task group, which doesn't reliably propagate exceptions
to an app-level catch-all `Exception` handler (they surfaced as an
`ExceptionGroup` instead, defeating the very hardening this phase was
adding). Replaced with a single pure-ASGI middleware class instead.

Phase 9 (Deployment — CI, production Docker images, deployment docs) and
its own bugs/decisions are covered above under "Continuous Integration"
and "Production Deployment" rather than repeated here.

**Phase 11 — the frontend has its first real screens.** Login, register
(auto-logs-in on success, matching the backend), a protected-route
wrapper, and an app shell (sidebar nav, header with org name + role,
logout) are implemented and verified against the live backend — not just
built and assumed to work. Token refresh is handled by an axios
interceptor: a 401 triggers `POST /auth/refresh` (de-duplicated across
concurrent requests), retries the original request once, and only forces
a redirect to `/login` if the refresh itself fails; auth endpoints
themselves are excluded from this flow so a wrong-password error shows
as a normal form message, not a forced logout.

- The UI kit is a small hand-rolled set (`Button`, `Input`, `Card`,
  `Alert`) rather than the shadcn/ui called out in the spec's tech stack
  — a deliberate simplification given how little UI exists so far,
  worth revisiting once there's enough screen surface to justify the
  setup cost.
- Tokens are stored in `localStorage`, not an `httpOnly` cookie — the
  backend's auth endpoints return tokens in the JSON response body (not
  a `Set-Cookie` header), so this is the pragmatic client-side choice
  matching the API as built, with the usual XSS-exposure tradeoff that
  implies.
- Still no frontend tests (`npm run test` has nothing to run) — that's
  Phase 17, per the spec's own phasing (Section 23 lists frontend
  testing as its own concern, separate from backend testing).

**Phase 12 — the dashboard is the first real data screen.** KPI cards
(revenue, orders, active customers, AOV), a revenue trend chart with a
day/week/month toggle, top products, customer activity, and recent
orders/tasks widgets all pull live data from the existing analytics/
orders/tasks endpoints. A shared `QueryState` component gives every
widget the same loading/error/empty handling from one place instead of
six hand-rolled copies, per the spec's explicit requirement (Section
15) that every widget handle all three states.

Verified against the live dev stack with real seeded data (one
customer, two products, two orders, one task) using Playwright driving
an actual browser: every widget rendered the correct numbers, the
granularity toggle worked, and there were no console errors.

**Bug caught by actually running it, not just building it:** after
writing all the Phase 12 files, the dashboard kept showing the old
Phase 11 "coming in Phase 12" placeholder even though the route already
pointed at the new component and the bind-mounted source was correct —
the long-running Vite dev server inside the Docker container needed a
restart to pick up the new route composition. A visual browser check
caught this immediately; `tsc`/`vite build` passing would not have.

- The revenue trend chart renders a single point when all activity
  falls on one day (as with the demo seed data above) — this is
  correct behavior, not a bug, but it means the chart's visual value
  is easier to appreciate once there's data spread across a longer
  window.

**Phase 13 — the first CRUD screens.** Customers and Products both get
full list/search/filter/pagination/create/edit/delete, replacing their
`ComingSoon` placeholders. New shared primitives (`Select`, `Modal`,
`ConfirmDialog`, `Pagination`, a `canWrite(role)` permission helper)
were built here and are reused as-is by both pages — the same
primitives will carry Orders and Tasks in Phase 14 without needing to
be rebuilt.

- Customers: search (name/email) + status filter (`active`/
  `inactive`/`at_risk`), create/edit in a modal, delete with a
  confirmation dialog.
- Products: category (free-text) filter + active/inactive filter,
  same create/edit/delete pattern.
- Write actions (the "New X" button and each row's Edit/Delete) are
  hidden entirely for `MEMBER`s, matching the backend's
  `require_role(Role.ADMIN)` enforcement — a `MEMBER` sees a read-only
  table with no way to even attempt a write that would 403.
- Verified live in a browser (Playwright): created, searched for,
  edited, and deleted a test customer and a test product against the
  running dev stack, with zero console errors. The frontend container
  was restarted before verification (per the lesson learned in Phase
  12) so a stale Vite dev-server session couldn't produce a false
  negative.

- Every section besides Dashboard, Customers, and Products (Orders,
  Tasks, AI Copilot, Reports, Imports) is still a shared `ComingSoon`
  placeholder — Phases 14–16 replace them one at a time.
- Table pagination has no page-size selector (fixed at 20 rows) — not
  a spec requirement, easy to add later if needed.
- Still no frontend tests (`npm run test` has nothing to run) — Phase
  17.
