# Contribution & Branching Rules — AI Operations Copilot

This document defines the Git workflow, branch naming conventions, commit
conventions, and release process for this repository. It is the source of
truth for how work moves from an idea to production. All contributors
(including AI-assisted commits) must follow it.

## 1. Branch Model

We use a Git Flow–style model with four long-lived branches and short-lived
supporting branches.

| Branch      | Purpose                                                   | Deploys to        | Protected |
|-------------|------------------------------------------------------------|--------------------|-----------|
| `main`      | Production-ready code only. Every commit is releasable.    | Production         | Yes       |
| `staging`   | Pre-production validation. Mirrors production config.      | Staging env        | Yes       |
| `develop`   | Integration branch. All features merge here first.         | Dev/preview env    | Yes       |
| `release/*` | Stabilization branch cut from `develop` before a release.  | Staging → Prod     | No        |

Supporting (short-lived) branches are created off `develop` and merged back
into `develop` via pull request. **Do not delete branches after merging** —
see Section 9 for the retention policy.

## 2. Branch Naming Convention

Format: `<type>/<phase-or-scope>-<short-description>`

| Type        | Used for                                              | Example                                  |
|-------------|--------------------------------------------------------|-------------------------------------------|
| `feature/`  | New functionality tied to a spec phase or module        | `feature/phase-1-auth-jwt`                |
| `phase/`    | A full development phase from the project spec          | `phase/2-core-data-models`                |
| `task/`     | Small, well-scoped chores or subtasks within a phase     | `task/phase-1-password-hashing`           |
| `fix/`      | Bug fixes                                                | `fix/tenant-isolation-leak`               |
| `hotfix/`   | Urgent production fixes, branched from `main`            | `hotfix/jwt-refresh-expiry`               |
| `refactor/` | Non-behavioral code restructuring                        | `refactor/ai-provider-interface`          |
| `chore/`    | Tooling, CI, dependency bumps, docs                       | `chore/ci-github-actions-setup`           |
| `release/`  | Release stabilization branch                             | `release/v0.1.0`                          |

Rules:
- All lowercase, hyphen-separated, no spaces or underscores.
- Always prefix with the phase number when the work maps to a spec phase
  (see `AI_Operations_Copilot_Project_Specification`, Section 27).
- Keep descriptions short (3–5 words) and specific to the change.

## 3. Branch Flow

```
feature/*, task/*, fix/*   ──PR──>  develop
develop                    ──PR──>  release/vX.Y.0
release/vX.Y.0             ──PR──>  staging   (QA / validation)
staging                    ──PR──>  main      (production tag + deploy)
main                       ──tag──> vX.Y.0
hotfix/*                   ──PR──>  main  AND  develop (backport)
```

- Never commit directly to `main`, `staging`, or `develop`.
- Every merge into `develop`, `staging`, or `main` happens via pull request
  with at least one review (self-review acceptable for solo portfolio work,
  but must include a written summary in the PR description).
- `release/*` branches only receive bug fixes and doc updates once cut —
  no new features.

## 4. Commit Message Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

<optional body — the "why", not the "what">
```

| Type       | Meaning                                      |
|------------|-----------------------------------------------|
| `feat`     | New feature                                    |
| `fix`      | Bug fix                                        |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test`     | Adding or correcting tests                     |
| `docs`     | Documentation only                             |
| `chore`    | Build process, tooling, dependencies           |
| `ci`       | CI/CD configuration                            |
| `perf`     | Performance improvement                        |
| `security` | Security-related fix or hardening              |

Scope examples: `auth`, `orgs`, `customers`, `orders`, `analytics`, `ai-gateway`,
`copilot`, `tasks`, `imports`, `reports`, `db`, `ci`, `frontend`.

Example:
```
feat(auth): add JWT refresh token rotation

Implements short-lived access tokens with rotating refresh tokens per
spec section 14 to reduce blast radius of a leaked refresh token.
```

## 5. Pull Request Requirements

Every PR must include:
- A clear title following the commit convention (`type(scope): summary`).
- A description of what changed and why.
- Reference to the relevant spec phase/section (e.g. "Implements Phase 1 — Auth").
- Confirmation that tests were added/updated and pass locally.
- Any new environment variables documented in `.env.example`.

PRs into `main` additionally require:
- All CI checks green (lint, type-check, tests, build).
- Version bump and changelog entry if applicable.

## 6. Versioning

Semantic Versioning (`MAJOR.MINOR.PATCH`):
- `MAJOR` — breaking API/schema changes.
- `MINOR` — new backward-compatible features (typically one per spec phase).
- `PATCH` — bug fixes, security patches, docs.

Pre-1.0 releases (beta/portfolio phase) use `0.MINOR.PATCH` and are tagged
from `main` after merging from `staging`.

## 7. Environment Parity

| Branch    | Environment | Notes                                             |
|-----------|-------------|----------------------------------------------------|
| `develop` | Dev         | Seeded/mock data, verbose logging, hot reload.     |
| `release/*` / `staging` | Staging | Production-like config, real migrations, seeded demo data (Acme Commerce). |
| `main`    | Production  | Real secrets via environment/secrets manager, no debug endpoints. |

## 8. What Never Gets Committed

- `.env` files with real secrets (only `.env.example` with placeholders).
- API keys, JWT signing secrets, database credentials.
- Generated artifacts (`__pycache__/`, `node_modules/`, `dist/`, `.venv/`).
- Direct commits to `main`/`staging`/`develop`.

## 9. Read This File First — Branch Reuse Policy

Before starting any task in this repository (human or AI-assisted), **read
this file first** to confirm the current branch/commit conventions are being
followed.

Before creating a new branch, check whether an existing branch already
covers the same task or a directly related one (same phase, same module,
same unmerged feature in progress):

- If the task is a continuation, fix, or refinement of work on an
  **existing, unmerged** branch, **reuse that branch** — commit to it rather
  than creating a new one. Check `git branch -a` and open PRs first.
- If the task is a genuinely new feature/phase/fix, create a new branch
  following the naming convention in Section 2.
- Never reuse a branch that has already been merged — cut a new one
  instead, even if the scope looks similar.
- When in doubt, prefer reuse for anything still in progress on `develop`;
  this keeps history efficient and avoids branch sprawl for what is
  effectively one unit of work.

**Branch retention — do not delete merged branches.** Once a branch (local
or remote) is merged into `develop`/`staging`/`main`, leave it in place
rather than deleting it, either via `git branch -d`/`-D` or `git push
origin --delete`. This applies to both local and remote copies. Keeping
merged branches around preserves a browsable per-phase history on GitHub
(useful for a portfolio project) and avoids accidentally destroying a
branch someone still has local commits or a PR referencing. Only delete a
branch when the user explicitly asks for that specific branch to be
removed.

## 10. Solo/Portfolio Workflow Note

This project is developed primarily by one contributor for portfolio
purposes. The branch model above is still followed in full — including PRs
against `develop`/`staging`/`main` — to demonstrate professional release
discipline, even without a team enforcing it. Self-merge is acceptable, but
skipping the branch flow (e.g. pushing directly to `main`) is not.
