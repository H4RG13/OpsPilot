# AI Operations Copilot

A multi-tenant business operations SaaS platform where a business imports
operational data, views analytics, asks an AI copilot questions about that
data, receives actionable recommendations, and automates recurring reports.
Built as a portfolio-grade, backend-focused full-stack project demonstrating
Python/FastAPI, PostgreSQL, React/TypeScript, AI model routing and tool
calling, background jobs, security, and testing.

> Status: **Phase 6 — Automation.** See `RULES.md` for the branching
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
npm run test
```

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

## Known Limitations (Phase 6)

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
