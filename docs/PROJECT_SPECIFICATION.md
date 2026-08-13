# AI Operations Copilot — Master Project Specification

> This is the implementation specification for the project, transcribed from
> the original planning document. Treat the architecture, requirements,
> boundaries, and phases below as the source of truth for implementation
> decisions. See `RULES.md` for how work on this spec is branched and
> committed.

**Primary goal:** Build a realistic, backend-focused SaaS application that
demonstrates Python, FastAPI, PostgreSQL, React, TypeScript, AI model
routing, tool calling, analytics, automation, security, testing, and
deployment.

**Target implementation:** Beta/portfolio first. Keep operating cost
extremely low while preserving production-style architecture so the AI
provider/models can be swapped later.

## 1. Product Vision

AI Operations Copilot is a multi-tenant business operations platform. A
business can import operational data, view analytics, ask an AI copilot
questions about that data, receive actionable recommendations, generate
tasks, and automate periodic reports.

The key differentiator is the AI Gateway/Model Router. The application does
not hard-code one LLM. It chooses a suitable model for a task and supports
provider/model fallback. The initial beta can use Groq-hosted models because
the project is cost-sensitive; the architecture must allow OpenAI or other
providers to be added later without changing business logic.

**Core product loop:** Business data → analytics → AI understanding →
recommendation → task/automation → measurable business action.

## 2. Portfolio Positioning

- Present it as an AI-enabled operations SaaS, not as a simple chatbot.
- Emphasize backend engineering: API design, domain modules, database
  design, AI orchestration, security, background jobs, testing,
  observability, and deployment.
- Frontend should be polished and modern but should support the backend
  rather than dominate the project.
- The beta must be demonstrable with seeded/mock business data so no real
  client data is required.
- The system should be designed for extensibility: AI providers, models,
  tools, integrations, and business modules should be replaceable.

## 3. MVP Scope

| Module | MVP Requirement |
|---|---|
| Authentication | Register/login, password hashing, JWT access/refresh tokens, logout/revocation strategy |
| Organizations | Multi-tenant organization, membership, roles, tenant isolation |
| Customers | CRUD, search, status, customer metrics |
| Products | CRUD, categories, price, active/inactive status |
| Orders | Orders + order items, status, totals, timestamps |
| Analytics | Revenue, order count, customer activity, product performance, date comparisons |
| AI Copilot | Chat with business context; tool calling into analytics/business data |
| AI Gateway | Provider abstraction, model routing, retries, fallback, usage tracking |
| Tasks | Create/update/assign/priority/status; AI can propose or create tasks |
| CSV Import | Upload and validate sales/customer/product data |
| Reports | Generate a weekly business summary using background jobs |
| Audit | Important user/admin/AI actions logged |

## 4. High-Level System Architecture

```
React + TypeScript
Dashboard / Copilot / CRUD
        │ HTTPS / JSON
        ▼
      FastAPI
API / Auth / Domain Modules
        │
    ┌───┴────────────┐
    ▼                ▼
PostgreSQL       AI Gateway
business data    routing/providers
    │               │
    │           GPT OSS 20B
    │           GPT OSS 120B
    │           Qwen 3.6 27B (vision)
    ▼
Redis + Celery
background jobs
reports/imports
```

Optional later: pgvector for embeddings/RAG, object storage for documents,
email/SMS provider, external business integrations, and additional AI
providers.

## 5. Recommended Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Language | Python 3.12+ | Primary backend language |
| API | FastAPI | Async REST API and dependency injection |
| Validation | Pydantic v2 | Request/response/config validation |
| ORM | SQLAlchemy 2.x | Database access |
| Migrations | Alembic | Schema migrations |
| Database | PostgreSQL | Primary relational database |
| Cache/Queue | Redis | Caching, Celery broker/result support |
| Jobs | Celery | Scheduled/background work |
| Frontend | React + TypeScript + Vite | Web application |
| Server State | TanStack Query | API caching and synchronization |
| UI | Tailwind CSS + shadcn/ui | Modern SaaS UI |
| Charts | Recharts | Analytics visualizations |
| AI | Groq initially | Low-cost beta AI inference |
| AI models | GPT OSS 20B/120B, Qwen 3.6 27B | Task-specific model routing |
| Testing | Pytest + HTTPX; Vitest/RTL | Backend/frontend tests |
| Containers | Docker + Compose | Reproducible development/deployment |
| CI | GitHub Actions | Lint/test/build automation |

## 6. Backend Architecture

```
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── security.py
│   │   └── logging.py
│   ├── modules/
│   │   ├── auth/
│   │   ├── organizations/
│   │   ├── users/
│   │   ├── customers/
│   │   ├── products/
│   │   ├── orders/
│   │   ├── analytics/
│   │   ├── tasks/
│   │   ├── imports/
│   │   ├── reports/
│   │   └── ai/
│   │       ├── router.py
│   │       ├── service.py
│   │       ├── providers/
│   │       ├── models/
│   │       ├── tools/
│   │       ├── prompts/
│   │       └── schemas.py
│   ├── shared/
│   │   ├── exceptions.py
│   │   ├── pagination.py
│   │   ├── permissions.py
│   │   └── utils.py
│   └── workers/
│       ├── celery_app.py
│       └── tasks.py
├── migrations/
├── tests/
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

**Module rule:** Router handles HTTP concerns; service contains business
logic; repository handles persistence where useful; schemas define API
contracts; models define persistence models. Do not place business logic
directly in route functions.

## 7. Frontend Architecture

```
frontend/
├── src/
│   ├── app/
│   │   ├── router.tsx
│   │   ├── providers.tsx
│   │   └── config.ts
│   ├── components/
│   │   ├── ui/
│   │   ├── layout/
│   │   ├── charts/
│   │   └── common/
│   ├── features/
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── customers/
│   │   ├── products/
│   │   ├── orders/
│   │   ├── analytics/
│   │   ├── tasks/
│   │   ├── imports/
│   │   ├── reports/
│   │   └── ai-copilot/
│   ├── lib/
│   │   ├── api.ts
│   │   └── query-client.ts
│   └── types/
└── package.json
```

## 8. AI Gateway and Model Router

This is the most important architectural feature. The business modules must
not call Groq/OpenAI directly. All LLM requests go through an internal AI
Gateway.

```
Application → AIService → ModelRouter
  task=summary            → GPT OSS 20B
  task=classification      → GPT OSS 20B
  task=business_analysis   → GPT OSS 120B
  task=complex_reasoning   → GPT OSS 120B
  task=image_analysis      → Qwen 3.6 27B
  task=vision              → Qwen 3.6 27B
                           → Provider Interface → GroqProvider → Groq API

Future: OpenAIProvider, AnthropicProvider, LocalProvider
```

Do not assume these exact model names are permanent. Keep model identifiers
in configuration/database and verify currently available models before
deployment.

## 9. AI Provider Interface

```python
class AIProvider(Protocol):
    async def generate_text(...): ...
    async def generate_structured(...): ...
    async def generate_with_tools(...): ...
    async def generate_vision(...): ...

class GroqProvider(AIProvider):
    ...

# Future:
class OpenAIProvider(AIProvider):
    ...
```

The rest of the application should depend on `AIProvider`/`AIService` rather
than a vendor SDK. This makes model/provider replacement straightforward and
demonstrates dependency inversion.

## 10. AI Tool Calling

The AI Copilot should not receive unrestricted database access. It should
call explicitly registered, validated tools.

Available tools (MVP):
- `get_revenue_summary(start_date, end_date)`
- `compare_revenue(period_a, period_b)`
- `get_top_products(start_date, end_date, limit)`
- `get_customer_metrics(start_date, end_date)`
- `get_at_risk_customers(limit)`
- `get_order_summary(start_date, end_date)`
- `search_customers(query, limit)`
- `create_task(title, description, priority, due_date)`
- `list_open_tasks(limit)`

Every tool must enforce the authenticated user's `organization_id`. Tool
arguments must be validated with Pydantic. Read tools should be safe by
default. Write tools such as `create_task` require explicit permission and
should be logged.

## 11. Example AI Request Flow

```
User: "Why did revenue drop last month?"

React
  → POST /api/v1/ai/chat
  → FastAPI authentication + organization context
  → AIService
  → ModelRouter → GPT OSS 120B
  → Model requests tool: compare_revenue(...)
  → Tool validates org_id + dates
  → PostgreSQL query
  → Tool result returned to model
  → Model produces structured explanation + recommendations
  → FastAPI validates response schema
  → Store AI message + usage metadata
  → React renders answer
```

## 12. Structured AI Response

```json
{
  "answer": "Revenue decreased by 21.7%...",
  "insights": [
    {
      "title": "Product A decline",
      "severity": "high",
      "evidence": "Revenue down 32%"
    }
  ],
  "recommendations": [
    "Investigate Product A",
    "Review returning-customer activity"
  ],
  "suggested_tasks": [
    {
      "title": "Investigate Product A",
      "priority": "high"
    }
  ]
}
```

Use structured outputs where supported. Never let the frontend depend on
unpredictable free-form parsing.

## 13. PostgreSQL Data Model

```
organizations
- id, name, created_at

users
- id, email, password_hash, full_name, created_at

organization_members
- organization_id, user_id, role

customers
- id, organization_id, name, email, status, lifetime_value, created_at

products
- id, organization_id, name, category, price, active, created_at

orders
- id, organization_id, customer_id, status, total_amount, ordered_at

order_items
- id, order_id, product_id, quantity, unit_price, subtotal

tasks
- id, organization_id, created_by, assigned_to, title, description,
  priority, status, due_date, created_at

ai_conversations
- id, organization_id, user_id, title, created_at

ai_messages
- id, conversation_id, role, content, model, provider, input_tokens,
  output_tokens, created_at

ai_usage
- id, organization_id, user_id, provider, model, task_type, input_tokens,
  output_tokens, latency_ms, estimated_cost, created_at

audit_logs
- id, organization_id, user_id, action, entity_type, entity_id, metadata,
  created_at
```

## 14. Multi-Tenancy and Security

- Every organization-owned table contains `organization_id`.
- Every service/repository query must enforce tenant scope.
- Never trust `organization_id` supplied by the browser; derive it from the
  authenticated membership/context.
- Implement role-based permissions: `OWNER`, `ADMIN`, `MEMBER`.
- Hash passwords with a modern password hashing algorithm.
- Use short-lived access tokens and a refresh-token strategy.
- Validate all inputs with Pydantic.
- Rate-limit AI endpoints to control abuse and cost.
- Never expose provider API keys to React.
- Store secrets only in environment variables/secrets management.
- Log security-sensitive events and AI write actions.
- Do not send unnecessary sensitive business data to an LLM.

## 15. Dashboard Requirements

The main dashboard should feel like a modern SaaS product.

- KPI cards: revenue, orders, customers, average order value.
- Revenue trend chart with date filters.
- Top products table/chart.
- Customer activity and at-risk count.
- Recent orders.
- Recent tasks.
- AI insights panel.
- Quick action: Ask Copilot.
- Loading, empty, error, and permission states for every major widget.

## 16. AI Copilot UI

```
┌─────────────────────────────────────────┐
│ AI Operations Copilot                    │
├─────────────────────────────────────────┤
│ User: Why did revenue drop this month?   │
│                                           │
│ AI: Revenue decreased 21.7%.             │
│                                           │
│ Key insights                             │
│  • Product A: -32%                       │
│  • Returning customers: -14%             │
│                                           │
│ Recommended actions                      │
│  [Create task] Investigate Product A     │
│  [Create task] Review customer retention │
│                                           │
│ Ask anything...                 [Send]   │
└─────────────────────────────────────────┘
```

## 17. CSV Import Pipeline

```
Upload CSV
  → File type/size validation
  → Parse + schema detection
  → Column mapping
  → Row validation
  → Preview errors
  → User confirms import
  → Batch insert/upsert
  → Import job status
  → Analytics refresh
```

AI may assist with column mapping, but deterministic validation must remain
the source of truth. Never let an LLM silently alter financial values.

## 18. Background Jobs

- Weekly business report generation.
- Large CSV processing.
- AI-heavy report generation.
- Optional email notification delivery.
- Periodic analytics aggregation if needed.
- Retry transient failures with bounded retries.
- Track job status so the UI can show queued/running/completed/failed.

## 19. Weekly AI Report

```
Weekly Business Report

Revenue: $245,300
Orders: 1,284
Growth: +12.4%

AI Insights
1. Returning customers increased 18%.
2. Product X declined 11%.
3. Support complaints increased 11%.

Recommended Actions
1. Investigate Product X.
2. Review recent support complaints.
3. Contact high-value inactive customers.
```

For the portfolio demo, reports can be generated from seeded data and saved
for viewing in the Reports page.

## 20. Future RAG Extension

RAG is not required for the first MVP. Add it after the core AI tool-calling
flow works.

```
Documents → Text extraction → Chunking → Embeddings
  → PostgreSQL + pgvector → Similarity search → Relevant chunks
  → LLM → Answer with source references
```

Possible documents: company policies, product manuals, refund policies,
SOPs, onboarding documents. The assistant should cite retrieved document
sources in its response.

## 21. API Design

```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout

GET    /api/v1/me
GET    /api/v1/organizations/current

GET    /api/v1/customers
POST   /api/v1/customers
GET    /api/v1/customers/{id}
PATCH  /api/v1/customers/{id}
DELETE /api/v1/customers/{id}

GET    /api/v1/products
POST   /api/v1/products

GET    /api/v1/orders
POST   /api/v1/orders

GET    /api/v1/analytics/overview
GET    /api/v1/analytics/revenue
GET    /api/v1/analytics/products
GET    /api/v1/analytics/customers

POST   /api/v1/ai/conversations
GET    /api/v1/ai/conversations
POST   /api/v1/ai/conversations/{id}/messages

GET    /api/v1/tasks
POST   /api/v1/tasks
PATCH  /api/v1/tasks/{id}

POST   /api/v1/imports/csv
GET    /api/v1/imports/{id}

GET    /api/v1/reports
POST   /api/v1/reports/generate

GET    /api/v1/ai/usage
```

## 22. Error Handling

```json
{
  "error": {
    "code": "CUSTOMER_NOT_FOUND",
    "message": "Customer was not found.",
    "request_id": "..."
  }
}
```

- Use consistent error responses.
- Generate/request a correlation ID for debugging.
- Never return stack traces to production clients.
- Translate provider errors into application-level errors.
- Distinguish validation, authentication, authorization, not-found,
  conflict, rate-limit, and upstream-provider errors.

## 23. Testing Strategy

- Unit-test services and business rules.
- API-test FastAPI routes with an isolated test database.
- Test tenant isolation explicitly.
- Test permission boundaries for OWNER/ADMIN/MEMBER.
- Test AI tool schemas and tool authorization.
- Mock the AI provider in most automated tests.
- Add a small number of integration tests against the real AI provider only
  when needed.
- Frontend-test critical forms, authentication states, and Copilot
  rendering.
- Test CSV validation with valid, invalid, duplicate, and malformed data.

## 24. Observability

- Structured application logs.
- Request IDs/correlation IDs.
- AI latency and token usage tracking.
- Model/provider/error metrics.
- Background job status and failures.
- Audit logs for important business and AI actions.
- Never log API keys, passwords, access tokens, or unnecessary private
  business data.

## 25. Cost-Control Strategy

This is a portfolio beta. The design must prioritize extremely low cost.

- Use Groq-hosted models for initial inference where available.
- Use GPT OSS 20B for simple/cheap tasks.
- Use GPT OSS 120B only for tasks that benefit from stronger reasoning.
- Use the vision model only for image tasks.
- Limit context size and tool results.
- Summarize long conversation history instead of repeatedly sending
  everything.
- Use caching where safe.
- Rate-limit AI requests per user/organization.
- Track token usage and estimated cost.
- Seed mock business data so the project can be demonstrated without real
  integrations.

**Cost principle:** Do not optimize for maximum model size. Optimize for the
cheapest model that reliably completes the task.

## 26. Model Routing Policy

| Task | Default Model |
|---|---|
| Short summary | GPT OSS 20B |
| Classification | GPT OSS 20B |
| Simple extraction | GPT OSS 20B |
| Customer complaint summary | GPT OSS 20B |
| Business analysis | GPT OSS 120B |
| Multi-step reasoning | GPT OSS 120B |
| Complex recommendations | GPT OSS 120B |
| Image analysis | Qwen 3.6 27B |

Fallback policy:
1. Retry transient provider failure.
2. If allowed, route to fallback model.
3. If all models fail, return a safe application error.
4. Log provider/model/latency/error.

## 27. Development Phases

| Phase | Deliverables |
|---|---|
| 0 — Setup | Monorepo, Docker Compose, FastAPI, React, PostgreSQL, Redis, environment config |
| 1 — Auth | Register/login, JWT, refresh, users, organization, roles |
| 2 — Core data | Customers, products, orders, migrations, CRUD, pagination/filtering |
| 3 — Analytics | Revenue/order/customer/product metrics and dashboard charts |
| 4 — AI Gateway | Provider interface, Groq provider, model router, usage logging |
| 5 — Copilot | Conversation API, tool calling, business-data questions, structured responses |
| 6 — Automation | Tasks, AI task suggestions, Celery, weekly reports |
| 7 — Imports | CSV upload, validation, mapping, background processing |
| 8 — Quality | Tests, security hardening, rate limits, error handling, audit logs |
| 9 — Deployment | Docker production build, CI, environment secrets, deployment, monitoring |
| 10 — Advanced | pgvector/RAG, additional providers, external integrations |

## 28. Definition of Done for MVP

- A user can register, create/join an organization, and authenticate
  securely.
- Tenant isolation is tested and enforced.
- Users can manage customers, products, orders, and tasks.
- Dashboard displays meaningful seeded business analytics.
- User can ask the AI why a metric changed.
- AI can call read-only analytics tools and return evidence-based
  structured insights.
- AI can propose a task and, with permission, create it.
- AI model selection is routed through the AI Gateway.
- AI usage and latency are recorded.
- CSV import works with validation and background processing.
- Weekly report can be generated.
- Automated tests cover core services, routes, security, and AI tool
  authorization.
- Application runs locally with Docker Compose.
- README documents architecture, setup, environment variables, demo
  credentials/data, API, and AI routing.

## 29. What NOT to Build Initially

- Do not build a huge agent framework.
- Do not add dozens of integrations before the core product works.
- Do not train a custom model.
- Do not add Kubernetes.
- Do not add microservices prematurely.
- Do not expose raw SQL/database tools to the LLM.
- Do not let the AI directly execute arbitrary code.
- Do not require paid infrastructure for the demo.
- Do not add RAG until tool calling and the core data model are stable.

## 30. Suggested Demo Scenario

Use a fictional small e-commerce company with enough seeded data to create
realistic analytics.

```
Demo company: Acme Commerce
Customers: 2,000+
Products: 50+
Orders: 10,000+
Date range: 12 months
```

Demo questions:
1. "Why did revenue drop last month?"
2. "What are our top 5 products?"
3. "Which customers are at risk?"
4. "Compare this month with the previous month."
5. "Create a task to investigate Product A."
6. "Summarize this week's business performance."

The demo should visibly show the AI using tools/data rather than
hallucinating an answer. Where practical, display the supporting metrics
used for an insight.

## 31. Portfolio README Requirements

- One-paragraph product pitch.
- Feature list.
- Architecture diagram.
- Technology stack.
- AI model-routing explanation.
- Security and multi-tenancy explanation.
- Database diagram.
- API documentation link/instructions.
- Local setup with Docker Compose.
- Environment variable template (`.env.example`).
- Seed/demo data instructions.
- Testing commands.
- Deployment instructions.
- Screenshots/GIF of dashboard and Copilot.
- Known limitations and future roadmap.

## 32. Claude Implementation Instructions

When implementing this project, work incrementally and preserve
architectural boundaries.

- First create the repository structure and development plan.
- Implement one vertical slice at a time: database → service → API →
  frontend.
- Keep modules small and cohesive.
- Use typed contracts everywhere.
- Prefer simple, understandable code over premature abstraction.
- Do not invent dependencies when existing stack capabilities are
  sufficient.
- Use migrations for all schema changes.
- Write tests alongside important functionality.
- Use mock AI responses in tests; never make the test suite depend on live
  LLM calls.
- Keep AI provider code isolated behind interfaces.
- Document decisions and update the README as architecture evolves.
- Never place secrets in source code.
- Do not claim a feature is complete until it has been implemented and
  tested.
- If an external model/API has changed, verify the current provider
  documentation before selecting a model identifier.

## 33. Recommended Initial Environment Variables

```
APP_ENV=development
APP_NAME=ai-operations-copilot
SECRET_KEY=change-me
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/ai_ops
REDIS_URL=redis://redis:6379/0

GROQ_API_KEY=
# Future:
OPENAI_API_KEY=

AI_DEFAULT_MODEL=gpt-oss-20b
AI_REASONING_MODEL=gpt-oss-120b
AI_VISION_MODEL=qwen-3.6-27b

FRONTEND_URL=http://localhost:5173
```

Do not commit real values. The exact Groq model IDs should be verified
against current provider documentation before implementation/deployment.

## 34. Final Architecture Principle

The most important design decision is separation of concerns:

```
React → FastAPI API → Domain Services → Repositories / PostgreSQL

AI requests:
Domain/API → AIService → ModelRouter → Provider → Model

Background work:
API → Celery → Redis → Worker → Database / AI / Reports
```

**Target learning outcome:** By completing this project, the developer
should be able to explain not only how to call an LLM, but how to build a
secure, testable, multi-tenant backend that uses AI as one component of a
larger software system.

## 35. Future Evolution Roadmap

- Add pgvector and document RAG.
- Add source citations to AI answers.
- Add OpenAI provider while keeping Groq as a low-cost option.
- Add configurable per-organization model policies.
- Add AI cost budgets and alerts.
- Add email notifications.
- Add CRM/helpdesk integrations.
- Add webhook ingestion.
- Add event-driven analytics.
- Add advanced audit/observability dashboards.
