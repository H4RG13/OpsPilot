# AI Operations Copilot

A multi-tenant business operations SaaS platform where a business imports
operational data, views analytics, asks an AI copilot questions about that
data, receives actionable recommendations, and automates recurring reports.
Built as a portfolio-grade, backend-focused full-stack project demonstrating
Python/FastAPI, PostgreSQL, React/TypeScript, AI model routing and tool
calling, background jobs, security, and testing.

> Status: **Phase 17 — Frontend Quality (final planned phase).** The full
> spec — backend and frontend — is implemented (see `PLAN.md`). Phase 10
> (Advanced: RAG, additional AI providers) remains optional/unstarted.
> See `RULES.md` for the branching
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

### Seeding demo data

```bash
docker compose exec backend python -m scripts.seed
```

Creates an "Acme Demo" organization with an OWNER account
(`demo@acme.example` / `supersecret123`) and an ADMIN account
(`admin@acme.example` / `supersecret123`) in the same organization —
useful for comparing what each role can see/edit — plus a sample
customer, two products, two orders, and a task. Safe to re-run: every
insert is guarded by a lookup, so running it again just reports the
existing accounts/data instead of duplicating anything.

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
npm run test    # Vitest + React Testing Library
npm run build   # tsc type-check + production build
```

## Continuous Integration

Every push and pull request runs [`.github/workflows/ci.yml`](.github/workflows/ci.yml):

- **Backend job:** `ruff check` then `pytest` — no service containers
  needed, since the whole suite runs against an in-memory SQLite database
  and injectable fakes for Redis/Celery/the LLM provider (see Known
  Limitations across every phase above for why that's true by design).
- **Frontend job:** `npm run lint` (ESLint), `npm run test` (Vitest +
  React Testing Library, added in Phase 17), then `npm run build`
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

## Known Limitations (Phase 17 — final planned phase)

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

- Table pagination has no page-size selector (fixed at 20 rows) — not
  a spec requirement, easy to add later if needed.

**Phase 14 — Orders and Tasks, the first screens with real
cross-entity relationships.** Orders reference a customer and one or
more products; Tasks reference an assignable user. Both replace their
`ComingSoon` placeholders with full list/filter/pagination/create/edit
screens, reusing the `Select`/`Modal`/`ConfirmDialog`/`Pagination`
primitives and `canWrite(role)` gating built in Phase 13 without any
changes to those primitives.

- Orders: status filter, a create-order flow with dynamic
  product + quantity rows and a client-side "estimated total" (labeled
  as such — the server always computes the real total and item unit
  prices, never trusting the client), a status-update `<select>` per
  row for `ADMIN`+, and a detail modal showing resolved product names,
  quantities, unit prices, and subtotals. There is no delete action —
  the backend has no `DELETE /orders/{id}` endpoint at all.
- Tasks: status + priority filters, create/edit modal. Editing also
  exposes a status field (creation defaults to `open` server-side, per
  the API).
- **Known gap called out rather than silently worked around:** the API
  supports assigning a task to a user (`assigned_to`), but there is no
  endpoint anywhere in the backend to list organization members, so a
  real "assign to teammate" dropdown has no data to populate. Rather
  than fake it with a raw UUID text box, Phase 14 ships a simple
  "Assign to me" checkbox using the current user's own ID from
  `useAuth()`, with assigning to teammates deferred until a
  list-members endpoint exists.
- The Orders page resolves `customer_id`/`product_id` to display names
  by fetching the customers/products lists at `page_size=100` and
  building a lookup map client-side (those endpoints return only IDs,
  not names). This assumes fewer than 100 of each — correct for this
  portfolio's demo data, but not how a real lookup would scale.
- Verified live in a browser (Playwright): created an order for an
  existing customer with 2 units of a product and confirmed the
  server-computed total ($99.98 for 2× $49.99) appeared correctly in
  both the list and the detail modal; updated an order's status;
  created and then edited a task (priority, status, self-assignment) —
  zero console errors throughout.
- Still no frontend tests (`npm run test` has nothing to run) — Phase
  17.

**Phase 15 — the AI Copilot, and three real backend bugs it finally
exposed.** Conversation list + "new conversation", a chat interface,
structured-answer rendering (insights with severity, recommendations,
suggested tasks each with a working "Create Task" button that calls
the existing `POST /tasks`), and a per-message `allow_ai_actions`
toggle (it's a per-message field on the backend, not per-conversation)
so the write-tool permission model built in Phase 6 is actually
reachable from the UI.

**Known gap, documented rather than faked:** the backend has no
endpoint to fetch a conversation's past messages — only
`POST .../messages` exists. Chat history is therefore client-side only,
scoped to the current browser session; reopening an older conversation
shows an empty thread until you send a new message.

**The frontend's honest 502 handling surfaced three real bugs in the
AI Gateway (Phases 4–5) that had only ever run against a mocked
provider in tests, never the live Groq API:**
1. The default Groq model IDs (`gpt-oss-20b`, `gpt-oss-120b`,
   `qwen-3.6-27b`, in both `config.py` and `.env`) were missing Groq's
   required provider prefix and 404'd on every call. Fixed by checking
   Groq's actual `/v1/models` catalog and correcting all three to
   `openai/gpt-oss-20b`, `openai/gpt-oss-120b`, `qwen/qwen3.6-27b`.
2. Tool-calling's follow-up messages were malformed per the
   OpenAI-compatible wire format Groq speaks: the assistant message
   never declared its `tool_calls`, and the tool-response message was
   missing the required `tool_call_id` — so any question that actually
   triggered a tool call 400'd. Fixed in `copilot_service.py`.
3. Groq's `function.arguments` field is always a JSON-encoded string,
   never a bare object, but `groq_provider.py` passed it straight into
   a Pydantic model expecting a `dict`, crashing on the first tool
   call. Fixed with a small parsing helper; the existing test's mock
   fixture (which used a bare dict, masking this) was corrected to
   match Groq's real format.

All three were invisible to the backend test suite (105/105 passed
throughout, before and after) because the suite's provider mock was
self-consistent with the bugs — this is exactly the kind of gap that
only shows up when you run the real thing against the real external
API, not just against your own mocks.

Verified live in a browser against the real Groq API: asked a revenue
question, got back a correct structured answer (right dollar figures,
right product breakdown) with all three answer sections rendering,
and confirmed "Create Task" on a suggestion actually created a task —
zero console errors.

**Phase 16 — Reports & Imports, the last data screens, and three more
real backend bugs found at the worker boundary.** Reports list with
status + a "Generate Report" action, automatic polling (react-query
`refetchInterval`, only while a report is `queued`/`running`) so
completion shows up without a manual refresh, and a report detail
modal — reusing Phase 15's `StructuredAnswer` component unmodified,
since a completed report's `summary` field is a JSON-encoded string
with the exact same shape as a Copilot answer. A CSV import screen
(`import_type` selector + file upload) shows total/imported/failed row
counts and a per-row error table, polling the job by ID every 2s while
it's in flight, with required-column hints shown per import type since
a missing column fails the whole job rather than individual rows.

**Known gaps, documented rather than faked:** there's no
`GET /reports/{id}` (only the paginated list) and no list endpoint for
import jobs at all (only upload + get-by-id) — so import history is
client-side only for the current session, the same pattern as Copilot
conversation history in Phase 15.

**Three more real bugs, all at the Celery task/worker-process boundary
that the backend test suite structurally can't reach** (105/105 tests
passed throughout, before and after every fix, because they exercise
the report/import *services* directly via DI-overridden dispatchers
and never run an actual Celery task against real Postgres):
1. Both `imports/tasks.py` and `reports/tasks.py` call
   `asyncio.run(...)` per task but shared one module-level asyncpg
   connection pool across those independent event loops — a pooled
   connection from one task's (now-closed) loop got reused by the
   next task, failing with
   `InterfaceError: cannot perform operation: another operation is in
   progress`. Every report/import got stuck at `queued` forever. Fixed
   with `await engine.dispose()` at the end of each task.
2. Once that was fixed, flushing a `Report`/`ImportJob` row failed
   with `NoReferencedTableError` — the worker process only imports its
   own task modules, never the full ORM model set the FastAPI app gets
   for free by importing every router at startup. Fixed by importing
   all models in `celery_app.py`, mirroring the list
   `migrations/env.py` already used for Alembic.
3. Not a code bug but a deployment gotcha worth documenting: after
   fixing Phase 15's Groq model IDs in `.env`, only the `backend`
   container had been recreated — the `worker` container was `restart`ed,
   which does **not** pick up `.env` changes, so it kept calling the
   broken model IDs until explicitly recreated with
   `docker compose up -d worker`.

Verified live against the real worker and real Postgres: generated a
report and watched it go `queued` → `completed` with correct data and
a fully rendered structured answer; uploaded a 3-row CSV with one
intentionally invalid row and got back `total: 3, imported: 2,
failed: 1` with the correct per-row error — zero console errors.

Every section in the spec's frontend scope is now built. Phase 17
(frontend testing) is what remains.

**Phase 17 — frontend testing, and the last bug this build found.**
Vitest + jsdom + React Testing Library (already sitting unused in
`package.json` since the Phase 0 scaffold) are wired up with a
`vite.config.ts` `test` block, a setup file, and a small
`renderWithProviders` helper. 11 tests across 5 files cover the
riskiest logic built across Phases 11–16: `LoginPage`/`RegisterPage`
(credential submission, client-side password-length validation,
error display without navigating away), `ProtectedRoute` (loading,
redirect, and authenticated states), and the Copilot's
`StructuredAnswer` (rendering, and "Create Task" actually calling
`POST /tasks`) and `ChatPanel`'s `allow_ai_actions` toggle (verifying
the exact payload sent for both checkbox states). `npm run test` now
passes and runs in CI, closing a gap documented since Phase 9.

The spec also calls for a responsive/accessibility pass across
Phases 11–16. Auditing every route at a 375px mobile viewport with
Playwright found a real bug: every table-bearing page (Customers,
Products, Orders, Tasks, Reports) caused the *entire page* to scroll
horizontally instead of just the table. Root cause was a classic
flexbox trap — `AppShell`'s content column was missing `min-w-0`, so a
flex child can't shrink below its content's intrinsic width and a wide
table forced the whole layout wider than the viewport. Fixed with
`min-w-0` on that column, `overflow-x-hidden` on `<main>`, and an
`overflow-x-auto` wrapper around all 6 `<table>` call sites — confirmed
with a before/after Playwright check that page-level horizontal
overflow went from present on 6 routes to present on none.

**Known gap, documented rather than solved here:** the sidebar is
fixed-width and doesn't collapse into a hamburger menu on small
viewports, so mobile users get a cramped (but no longer broken)
content column. A real mobile nav is a distinct, larger feature than a
horizontal-overflow fix.

**Pre-existing, out of scope for this phase:** `npm audit` flags
`react-router` (fix requires v6 → v7) and `esbuild`/`vite` (fix
requires a new `vite` major) advisories — both are their own
migrations, not testing work, and are left as known follow-ups.

**This closes out the frontend roadmap.** Phases 11–17 built every
screen in the spec, backed by real API calls, catching and fixing real
bugs — in the frontend, the AI Gateway, and the Celery workers — at
every step by actually running the app instead of trusting builds and
mocks. Phase 10 (Advanced: RAG, additional AI providers, per-org model
policy) remains the only unstarted, explicitly optional scope from the
original spec.
