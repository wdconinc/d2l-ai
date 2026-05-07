# d2l-ai — Brightspace (D2L) AI Integration

An AI integration for the [D2L Brightspace](https://www.d2l.com/) LMS, targeted at **instructors and course developers** at the University of Manitoba.

The integration is built as a standards-based **LTI 1.3 / LTI Advantage tool** plus a Brightspace REST API client, with a provider-agnostic LLM gateway and Retrieval-Augmented Generation over instructor-authored course materials.

## Documents

- 📄 **[Development plan](docs/brightspace-ai-integration-plan.md)** — full architecture, roadmap, privacy, and tickets.
- ♿ **[Accessibility guide](docs/accessibility-wcag-2.1-aa.md)** — WCAG 2.1 AA expectations, axe-core CI gate, and manual test checklists.
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

## License

MIT — see [LICENSE](LICENSE).
