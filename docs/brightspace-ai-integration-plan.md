# UManitoba Brightspace (D2L) AI Integration — Development Plan

**Owner:** UManitoba (LMS / Centre for Advancement of Teaching & Learning)  
**Target platform:** D2L Brightspace (SaaS, Canadian data centre)  
**Primary users:** Instructors and Course Developers / Instructional Designers  
**Status:** Draft v0.1 — ready for agent-driven scaffolding  
**Repository:** https://github.com/wdconinc/d2l-ai

---

## 1. Goals & Non-Goals

### 1.1 Goals

- Provide instructors and course developers with **AI assistance embedded inside Brightspace** for the high-effort, low-creativity parts of course design and delivery.
- Use UManitoba-approved LLM providers, with **all PII and course content kept in Canadian jurisdiction** (FIPPA / PHIA compliant).
- Be **additive to D2L Lumi**, not duplicative — focus on UM-specific workflows, bring-your-own-LLM, and Retrieval-Augmented Generation (RAG) over the instructor's own materials.
- Ship as a **standard LTI 1.3 Advantage tool** so it can be deployed to any future LMS with minimal rework.

### 1.2 Non-Goals for v1

- Student-facing tutoring chatbots.
- Replacing or wrapping D2L Lumi's UI.
- Auto-grading of summative assessments.
- Modifying the Brightspace platform itself.

---

## 2. Target Use Cases

| # | Use case | Inputs | Outputs | Surface |
|---|---|---|---|---|
| U1 | Syllabus drafting from course outline + UM templates | Course code, calendar entry, learning outcomes | Draft syllabus aligned with UM Senate policy | LTI tool, Deep Link → Content |
| U2 | Module summary / overview generation | Existing topics in a module | Markdown overview, learning outcomes, time-on-task estimate | LTI tool |
| U3 | Quiz / question bank generation with Bloom-level targeting | PDF/DOCX/HTML readings | Items pushed to Brightspace Question Library via REST API | LTI tool + REST write-back |
| U4 | Rubric generation | Assignment description, outcome map | Rubric created in Brightspace via API | LTI tool + REST |
| U5 | Draft feedback suggestions on dropbox submissions | Submission text, rubric | Suggested per-criterion feedback, instructor edits before release | LTI launch from Assignments |
| U6 | Course-quality review | Whole course | Alignment, accessibility, broken links, readability report | Background job + dashboard widget |
| U7 | Accessibility / plain-language rewrite of HTML topics | Topic HTML | Improved HTML, alt text suggestions, reading-level notes | LTI tool inline |
| U8 | Course Q&A copilot for instructors | Natural-language question | Cited answer over course shell | Course homepage widget |
| U9 | Translation / bilingual content | Topic content | Translated content + terminology notes | LTI tool |
| U10 | Outcome / competency mapping check | Course content + outcome list | Heatmap of where each outcome is taught/assessed | Background + dashboard |

**v1 priority:** U2, U3, U4, U7, U8.

---

## 3. Brightspace Integration Surfaces

### 3.1 Primary: LTI 1.3 / LTI Advantage

Use LTI 1.3 as the primary integration mechanism.

Required sub-services:

- **Core LTI 1.3 launch** for instructor SSO and course context.
- **Names and Role Provisioning Service (NRPS)** to verify roles and avoid exposing instructor-only tools to students.
- **Deep Linking 2.0** to return AI-generated content items into Brightspace modules.
- **Assignment and Grade Services (AGS)** only if and when U5 creates grade items or feedback flows.

Recommended placements:

- Course navbar link: “UM AI Assistant”.
- Content tool deep-linking placement.
- Optional assignment-context launch for draft feedback.

### 3.2 Secondary: Brightspace REST APIs

Use the Brightspace REST APIs for operations outside LTI's scope and for server-side read/write workflows.

Important endpoint families:

- `/d2l/api/lp/{version}/users/whoami`
- `/d2l/api/le/{version}/{orgUnitId}/content/...`
- `/d2l/api/le/{version}/{orgUnitId}/quizzes/...`
- `/d2l/api/le/{version}/{orgUnitId}/questionLibrary/...`
- `/d2l/api/le/{version}/{orgUnitId}/rubrics/...`
- `/d2l/api/le/{version}/{orgUnitId}/dropbox/...`
- `/d2l/api/lp/{version}/enrollments/...`

Authentication:

- Register an OAuth 2.0 client in the Brightspace tenant.
- Use refresh-token persistence for service operations.
- Store tokens encrypted at rest.

### 3.3 Tertiary: Custom Widgets / Remote Plugins

Use widgets or iframe-based remote surfaces for:

- U8 instructor course Q&A copilot.
- U6 course-quality dashboard tiles.
- Lightweight course-homepage recommendations.

### 3.4 Background Data: Brightspace Data Sets / Data Hub

Use Brightspace Data Sets for longitudinal analytics and batch course-audit jobs.

---

## 4. Reference Architecture

```text
┌──────────────────────── Brightspace (D2L SaaS, Canada) ────────────────────────┐
│ Instructor browser ──LTI 1.3 launch──► UM AI Tool launch UI                     │
│ Brightspace REST API ◄──OAuth2──────── Backend Brightspace client               │
└───────────────────────────────────────────────┬─────────────────────────────────┘
                                                │ HTTPS
                                                ▼
┌──────────────────── UM-hosted backend, Azure Canada Central / UM on-prem ───────┐
│ FastAPI API gateway                                                              │
│ ├── LTI 1.3 service: JWKS, launch, NRPS, deep-linking                            │
│ ├── Brightspace REST client: OAuth2, retries, typed clients                      │
│ ├── Workflow orchestrator: Celery / Redis                                        │
│ ├── RAG service: Postgres + pgvector                                             │
│ ├── LLM gateway: Azure OpenAI CA / Anthropic Bedrock CA / on-prem vLLM           │
│ ├── PII scrubber + content-safety filters                                        │
│ ├── Audit log + provenance metadata                                              │
│ └── Admin console                                                                │
└──────────────────────────────────────────────────────────────────────────────────┘
```

Cross-cutting requirements:

- Tenant isolation.
- Per-course vector namespaces.
- No model training on UM data.
- Prompt/response audit logging with retention controls.
- Instructor approval before write-back.

---

## 5. Technology Choices

| Concern | Choice | Rationale |
|---|---|---|
| Backend | Python 3.12 + FastAPI | Strong LLM ecosystem and async API support |
| LTI | `pylti1p3` | Mature LTI 1.3 / Advantage support |
| Frontend | React 18 + Vite + Lit components | Modern UI with ability to fit Brightspace look and feel |
| Admin console | Next.js 14 | Common admin UI stack |
| DB | PostgreSQL 16 + pgvector | Relational metadata + embeddings in one store |
| Queue | Celery + Redis | Background course indexing and audits |
| LLM providers | Azure OpenAI Canada Central; Anthropic via Bedrock ca-central-1; on-prem vLLM fallback | Data residency and provider portability |
| Infra | Terraform to Azure Canada Central | Canadian hosting and repeatable deployment |
| Observability | OpenTelemetry + Grafana/Loki | Operational visibility |
| CI/CD | GitHub Actions + OIDC | Secure deployments without long-lived cloud secrets |

---

## 6. Data, Privacy & Compliance

- **Jurisdiction:** All processing and storage must remain in Canada.
- **Primary legislation:** Manitoba FIPPA; PHIA considerations for health-related course material.
- **Course content:** internal institutional data; may be sent to contracted in-Canada LLM endpoints after PII scrub.
- **Student submissions:** confidential; require explicit opt-in and additional governance before U5.
- **Rosters:** used to verify instructor role; never sent to an LLM.
- **Prompt logs:** retained for 90 days by default, then purged, unless policy requires otherwise.
- **Vendor contracts:** no training, zero retention or agreed retention, Canadian processing.
- **Transparency:** AI-generated content is labelled as draft and includes provenance metadata.
- **Accessibility:** WCAG 2.1 AA required.
- **Bilingual:** English/French UI support.
- **Indigenous content:** assist-only mode and consultation before any workflow focused on Indigenous content or terminology.

---

## 7. Roadmap

### Phase 0 — Discovery & Approvals, 4 weeks

- Stakeholder interviews: CATL, LMS team, instructors, privacy, Indigenous Engagement, Accessibility Services.
- Confirm non-production Brightspace sandbox access.
- Register LTI tool and OAuth client in sandbox.
- File DPIA / PIA.
- Select LLM provider and execute data-processing agreement.

**Exit criteria:** signed scope, sandbox access, DPIA accepted.

### Phase 1 — Foundation, 6 weeks

- Repository scaffold.
- Terraform foundation for Azure Canada Central.
- LTI 1.3 launch and Deep Linking end-to-end.
- Brightspace REST OAuth2 client.
- LLM gateway with PII scrubber and audit log.
- Basic React/Lit launch UI.

**Exit criteria:** tool launches in sandbox, can list course modules, and can deep-link a static HTML topic.

### Phase 2 — MVP Features, 10 weeks

- U2 module summary.
- U3 quiz/question generation to Question Library.
- U7 accessibility/plain-language rewrite.
- Admin console for tenant settings, model selection, usage metering.

### Phase 3 — Pilot, 8 weeks

- U4 rubric generation.
- U8 course Q&A copilot widget.
- RAG indexing pipeline.
- Production pilot with feature flags.

### Phase 4 — General Availability

- U5 draft feedback with consent gating.
- U6 course-quality dashboard.
- U9 translation.
- U10 outcome mapping.

---

## 8. Target Repository Layout

```text
um-brightspace-ai/
├── README.md
├── LICENSE
├── docs/
│   ├── architecture.md
│   ├── lti-registration.md
│   ├── api-mapping.md
│   ├── privacy-dpia.md
│   └── prompts/
├── infra/
│   └── terraform/
├── apps/
│   ├── api/
│   │   ├── pyproject.toml
│   │   ├── app/
│   │   │   ├── lti/
│   │   │   ├── brightspace/
│   │   │   ├── llm/
│   │   │   ├── rag/
│   │   │   ├── workflows/
│   │   │   ├── audit/
│   │   │   └── main.py
│   │   └── tests/
│   ├── web/
│   └── admin/
├── packages/
│   └── shared-types/
└── .github/
    ├── workflows/
    └── copilot-instructions.md
```

---

## 9. Phase 1 Tickets for Agent Implementation

These tickets are intended to be opened as GitHub issues and assigned to `@copilot` where supported.

### 1. infra: terraform skeleton for Azure Canada Central

Create Terraform modules for resource group, Azure Container Apps or AKS placeholder, PostgreSQL Flexible Server with pgvector, Redis, Key Vault, Log Analytics, and managed identities.

### 2. api: bootstrap FastAPI app

Create `apps/api` with FastAPI, Pydantic settings, health endpoints, structured logging, OpenTelemetry hooks, pytest, ruff, black, mypy, and Dockerfile.

### 3. api/lti: implement LTI 1.3 registration and launch

Use `pylti1p3` to implement JWKS, OIDC login, launch validation, state/nonce persistence, and course-context extraction.

### 4. api/lti: implement Deep Linking 2.0 response builder

Build a Deep Linking response endpoint capable of returning an HTML topic/link content item to Brightspace.

### 5. api/brightspace: OAuth2 client with refresh-token persistence

Implement Brightspace OAuth2 token handling, encrypted refresh-token persistence, and a `whoami` integration test.

### 6. api/brightspace: typed clients for content, quizzes, question library, rubrics

Create thin typed Pydantic clients for the Brightspace endpoints required by U2, U3, and U4.

### 7. api/llm: provider-abstraction gateway

Implement an LLM gateway abstraction and adapters for Azure OpenAI, Anthropic via Bedrock, and vLLM; include PII scrubbing and audit logging.

### 8. api/workflows/u2_module_summary

Implement module summary workflow: fetch module topics, extract text, summarize, and return preview plus Deep Linking payload.

### 9. api/workflows/u3_quiz_generation

Implement quiz/question generation workflow: generate question JSON, validate schema, preview to instructor, and write to Question Library only after confirmation.

### 10. web: Lit-based LTI launch UI

Create `apps/web` with React + Vite, use-case picker, workflow forms, preview pane, confirmation dialog, i18n scaffolding, and Brightspace-compatible styling.

### 11. docs: prompts/versioned prompt library and eval harness

Create a prompt library under `docs/prompts/` with versioning, golden-input tests, and regression hooks.

### 12. security: prompt-injection test suite

Add tests for prompt-injection and data-exfiltration resistance across RAG and HTML rewrite workflows.

### 13. ops: usage metering and budget caps

Add per-tenant usage tracking for launches, tokens, workflows, provider costs, and configurable budget limits.

### 14. a11y: WCAG 2.1 AA audit and axe-core CI gate

Add accessibility CI checks for the web/admin apps and document manual keyboard/screen-reader test steps.

---

## 10. Issue Template Guidance

Each Phase 1 issue should include:

- Objective.
- Scope.
- Implementation notes.
- Acceptance criteria.
- Sandbox test steps.
- Brightspace endpoints touched.
- Security/privacy notes.
- Labels: `phase-1`, `agent-ready`, and an area label such as `infra`, `api`, `lti`, `brightspace`, `llm`, `web`, `docs`, `security`, `ops`, or `a11y`.

---

## 11. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---:|---:|---|
| D2L expands Lumi to cover more use cases | High | Medium | Focus on UM-specific RAG, sovereignty, policy and ID workflows |
| Brightspace REST rate limits | Medium | Medium | Cache reads, batch writes, exponential backoff |
| LLM hallucination | High | High | Draft-only, provenance, eval harness, instructor confirmation |
| Privacy review delays | Medium | High | Engage privacy in Phase 0 |
| Faculty resistance | Medium | High | Governance group, opt-in pilot, transparency |
| Vendor lock-in | Medium | Medium | Provider abstraction and on-prem fallback |
| Indigenous-content harms | Low | Very high | Consult before release; assist-only mode |

---

## 12. Success Metrics

- ≥ 25 active instructors in pilot semester.
- ≥ 30 minutes median self-reported time saved per accepted artifact.
- ≥ 80% of generated quiz questions accepted with edits.
- 99.5% successful LTI launches.
- p95 latency < 4 seconds for non-RAG workflows and < 10 seconds for RAG workflows.
- Zero data-residency incidents.
- 100% WCAG 2.1 AA CI gate pass rate.

---

## 13. Open Questions

1. Which LLM provider contract can UM execute fastest?
2. Is on-prem vLLM hosting desirable for maximum sovereignty?
3. Which Brightspace sandbox tenant and API versions will be used?
4. What is the policy stance on AI-assisted feedback on student submissions?
5. Should the project remain public open source or become UM-internal after pilot?

---

## 14. References

- Brightspace Developer Platform: https://developer.brightspace.com/
- Brightspace REST API / Valence docs: https://docs.valence.desire2learn.com/
- Brightspace LTI documentation: https://community.d2l.com/brightspace/kb/articles/143-brightspace-learning-tools-interoperability-lti
- IMS LTI 1.3 / Advantage: https://www.imsglobal.org/spec/lti/v1p3/
- `pylti1p3`: https://github.com/dmitry-viskov/pylti1.3
- pgvector: https://github.com/pgvector/pgvector
- Manitoba FIPPA: https://web2.gov.mb.ca/laws/statutes/ccsm/f175e.php
