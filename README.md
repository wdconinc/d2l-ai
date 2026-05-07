# d2l-ai — Brightspace (D2L) AI Integration

An AI integration for the [D2L Brightspace](https://www.d2l.com/) LMS, targeted at **instructors and course developers** at the University of Manitoba.

The integration is built as a standards-based **LTI 1.3 / LTI Advantage tool** plus a Brightspace REST API client, with a provider-agnostic LLM gateway and Retrieval-Augmented Generation over instructor-authored course materials.

## Documents

- 📄 **[Development plan](docs/brightspace-ai-integration-plan.md)** — full architecture, roadmap, privacy, and tickets.
- 🤖 **[.github/copilot-instructions.md](.github/copilot-instructions.md)** — repo-wide guidance for the GitHub Coding Agent.

## Status

Draft v0.1 — Phase 0 (discovery & approvals). Phase 1 implementation tickets are tracked as [GitHub Issues](https://github.com/wdconinc/d2l-ai/issues).

## Goals

- Provide instructors and course developers with **AI assistance embedded inside Brightspace** for high-effort, low-creativity course design and delivery tasks.
- Use UManitoba-approved LLM providers, with **all PII and course content kept in Canadian jurisdiction** (FIPPA / PHIA compliant).
- Be **additive to D2L Lumi**, not duplicative — focus on UM-specific workflows, BYO-LLM, and RAG over the instructor's own materials.

## High-level architecture

```
Brightspace ──LTI 1.3──► UM AI Tool (FastAPI + React/Lit)
          ◄──REST API──   ├─ LLM gateway (Azure OpenAI CA / Anthropic / vLLM)
                          ├─ pgvector RAG
                          └─ Audit + PII scrub
```

See [`docs/brightspace-ai-integration-plan.md`](docs/brightspace-ai-integration-plan.md) for details.

## Usage metering (draft implementation)

- API app entrypoint: `apps/api/app/main.py`
- Admin endpoints:
  - `POST /admin/tenants/{tenant_id}/budget-caps`
  - `GET /admin/tenants/{tenant_id}/budget-caps`
  - `GET /admin/tenants/{tenant_id}/usage`
- Metered LLM-call endpoint: `POST /tenants/{tenant_id}/llm/calls`
- Auth:
  - Admin endpoints require `Authorization: Bearer <token>` matching `D2L_AI_ADMIN_API_TOKEN`
  - LLM-call endpoint requires `Authorization: Bearer <token>` matching `D2L_AI_LLM_CALL_TOKEN`
- Targeted tests: `PYTHONPATH=apps/api python -m pytest apps/api/tests -q`

## License

MIT — see [LICENSE](LICENSE).
