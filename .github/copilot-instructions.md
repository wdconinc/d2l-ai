# Copilot / Coding Agent Instructions — d2l-ai

This repository implements an **AI integration for D2L Brightspace** targeted at instructors and course developers. Read [`docs/brightspace-ai-integration-plan.md`](../docs/brightspace-ai-integration-plan.md) before making non-trivial changes.

## Stack (authoritative)

- **Backend:** Python 3.12, FastAPI, `pylti1p3` for LTI 1.3 / Advantage, Pydantic v2, SQLAlchemy 2.x, Alembic, Celery + Redis.
- **Database:** PostgreSQL 16 with the `pgvector` extension (single store for relational + embeddings).
- **Frontend (LTI launch UI):** React 18 + Vite, with Lit web components where it improves visual fit with Brightspace.
- **Admin console:** Next.js 14 (App Router).
- **LLM gateway:** provider abstraction with adapters for **Azure OpenAI (Canada Central)**, **Anthropic Claude via AWS Bedrock (ca-central-1)**, and **on-prem vLLM** (Llama 3.1 70B). Never hard-code a provider in workflow code.
- **Infrastructure:** Terraform → Azure Canada Central. CI/CD via GitHub Actions, OIDC to Azure.
- **Observability:** OpenTelemetry → Grafana / Loki.

## Repository layout (target)

```
apps/api/         # FastAPI backend
apps/web/         # React + Lit LTI launch UI
apps/admin/       # Next.js admin console
packages/shared-types/  # OpenAPI + generated TS types
infra/terraform/<provider>/  # Provider-specific infra stacks (azure, future providers)
docs/             # Architecture, prompts, DPIA
.github/workflows/
```

## Hard rules

1. **Data residency:** All processing, storage, and LLM calls MUST stay in Canadian regions. Do not introduce dependencies that egress to US/EU endpoints by default.
2. **PII scrubbing:** Every prompt sent to an LLM MUST go through the `app/llm/scrub.py` middleware. Student names/IDs from NRPS rosters MUST never reach the LLM.
3. **Draft, never auto-publish:** AI-generated artifacts (quiz items, rubrics, topic HTML, feedback) are returned to the instructor for review. Workflows MUST NOT POST to Brightspace REST without explicit instructor confirmation in the UI, except for clearly background/read-only operations (e.g., U6 audit reports).
4. **Provenance:** Every generated artifact carries metadata `{model, prompt_hash, version, generated_at}`. HTML topics include an HTML comment `<!-- generated-by: UM-AI-Tool vX, model=…, prompt-hash=… -->`.
5. **Accessibility:** All UI MUST pass WCAG 2.1 AA; `axe-core` checks are a CI gate.
6. **Bilingual:** All user-facing strings are i18n keys (EN + FR).
7. **Auth:** Instructors authenticate ONLY via LTI 1.3 launch (JWT). Admin console uses UM Entra ID SSO. Never invent a separate password store.
8. **Tests:** New backend code requires pytest unit tests; new workflows require an entry in the prompt eval harness (`docs/prompts/`).

## Brightspace specifics

- LTI registration is per-tenant; configuration is loaded from environment + DB, never committed.
- REST API base: `https://{tenant}.brightspace.com/d2l/api/`. Use the OAuth2 refresh-token flow; persist tokens in `app.brightspace.tokens`.
- Common endpoints used: `/lp/{v}/users/whoami`, `/le/{v}/{orgUnitId}/content/...`, `/le/{v}/{orgUnitId}/quizzes/...`, `/le/{v}/{orgUnitId}/questionLibrary/...`, `/le/{v}/{orgUnitId}/rubrics/...`, `/le/{v}/{orgUnitId}/dropbox/...`.
- Respect rate limits: cache GETs for 5 min by default, batch writes, exponential backoff on 429/503.

## Style

- Python: `ruff` + `black` (line length 100), type hints required, `mypy --strict` in CI.
- TypeScript: `eslint` + `prettier`, strict mode on.
- Conventional Commits.
- One Phase-1 ticket = one PR where possible.
