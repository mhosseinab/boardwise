---
type: plan
tags: [github-portfolio, boardwise, llm-agent, langchain, migration-orchestration, implementation-plan]
project: "[[05-domain-specific-paddleboard-agent]]"
slug: domain-specific-paddleboard-agent
status: ready
created: 2026-07-09
---

# BoardWise (Project 05) — Greenfield build of a domain-constrained SUP gear agent

**Status: READY TO EXECUTE (2026-07-09).** Build, from zero, the BoardWise portfolio repo: a
LangChain tool-calling agent strictly scoped to SUP gear, grounded in a seeded SQLite catalog, with
a code-level grounding guardrail, refusal backstop, eval harness, consumer-facing React UI, Docker
Compose packaging, and CI. Everything ships offline-verifiable; live-model runs and publishing are
gated at the end.

> Supersedes: `Projects/github-portfolio/Plans/05-domain-specific-paddleboard-agent-plan.md` (prior
> high-level plan — its phases, risks, and dependency lanes are carried forward and tightened here).
> Authoritative spec: `Projects/github-portfolio/05-domain-specific-paddleboard-agent.md` (the build
> brief; S1 copies it into the repo as `docs/SPEC.md` so workers can read it in-repo).
> Companions: `domain-specific-paddleboard-agent-implementation-steps.md` (the how),
> `domain-specific-paddleboard-agent-workflow.md` (the driver),
> `domain-specific-paddleboard-agent-progress.md` (durable state).

---

## 0. Conventions are PRESCRIBED, not discovered

This is a **greenfield** project — there is no repo to grep, so the skill's Phase-1 discovery is
replaced by prescription. All conventions below are derived from the tech stack the spec pins
(spec §"Tech stack", §"Testing", §"CI") and **S1 must scaffold every one of them** (git init,
`pyproject.toml`, lockfiles, lint/type/test config, Makefile, CI skeleton comes at S21):

| Convention | Prescribed value (S1 creates it) |
|---|---|
| Repo root | `~/workspace/boardwise` (default; override at launch — see workflow doc `args`) |
| Trunk / integration branch | `main` (fresh repo — trunk IS the integration branch) |
| Per-step branches | `s<NN>-<short-title>` off `main`, merged on review PASS |
| Commits | Conventional Commits (`feat:`, `test:`, `chore:`, `docs:`); stage files by name, never `git add -A` |
| Python verify | `cd backend && ruff check . && black --check . && mypy app && pytest -q` |
| Frontend verify | `cd frontend && npm run lint && npx tsc --noEmit && npx vitest run && npm run build` |
| E2E verify | `cd frontend && npx playwright test` (offline — API mocked via route interception) |
| Packaging verify | `docker compose build` exit 0; `docker compose up -d` + health curls; `docker compose down -v` |
| Eval verify | `make eval` (offline against the mocked model; live models only at gate S24) |
| Rules doc | repo `README.md` + `docs/SPEC.md` (S1); prompts documented in `backend/app/prompts/README.md` (S8) |
| Codegen | none — TS types in `frontend/src/lib/types.ts` are **hand-mirrored** from `backend/app/schemas.py`, frozen at S4 (see fork §4.8) |
| Flag/rollout mechanism | none needed — greenfield dark-shipping reduces to **additive-only** steps: nothing is on a live path until S26 publishes |

## 1. Why, and the honest scope

**End state:** a public GitHub repo (`boardwise`) that a hiring manager clones and runs with one
command: `docker compose up` serves a seeded catalog UI on `:3006` and the API on `:8006`; the
agent answers SUP-gear questions only from tool results, says "I don't have that spec" when the DB
lacks an answer, refuses off-topic prompts with zero tool runs, and ships an eval harness that
measures (not asserts) correctness, grounding, and refusal rate. CI is green; the README carries a
demo GIF, a Mermaid pipeline diagram, live-model eval numbers, and an unmissable mock-data notice.

**What does NOT change / does NOT get built (say it plainly):** no real product data, scraping, or
real brand names — all data is synthetic and fictional; no commerce (cart/checkout/payments); no
auth, user accounts, or chat-history persistence; no RAG over unstructured docs (the env-flagged
fuzzy-search stretch goal is excluded from this plan entirely); no multi-tenancy, rate limiting, or
production hardening; no mobile/i18n; no fine-tuning; no Postgres swap. Stretch goals are **out of
this plan** — they start only after S26 lands, as new scoped work. Vault documents (this plan set)
are read-only inputs to the run; the run never edits them except the progress file.

**Why it's lower-risk than it sounds:** the spec is unusually complete — contracts, ports, repo
layout, and acceptance criteria are already pinned, so almost every step is mechanical against a
written target. The genuinely risky pieces are exactly two: the grounding validator's precision
(unit conversion / rounding / derived-arithmetic edge cases — §10 R1) and provider variance in tool
calling (§10 R2). Both are isolated into their own steps (S9, S24) with dedicated verifies.

## 2. Current state (verified against the vault 2026-07-09)

> Greenfield: **no code exists**. "Current state" = the two authoritative documents. Every row
> anchors to them, not to imaginary files.

| Piece | Location | Status today |
|---|---|---|
| Project status | `Projects/github-portfolio/05-domain-specific-paddleboard-agent.md:9` | "Idea / spec — not started … no code exists yet" |
| Full build brief (stack, contracts, layout, DoD) | same file, lines 36–219 | complete spec; ports 3006/8006, stack pinned, acceptance checklist at lines 207–215 |
| Declared assumptions | same file, lines 223–228 + `<!-- ASSUMED: ... -->` markers at lines 9, 188 | five spec assumptions + two inline markers — carried into §4 below as resolved-by-default, **not** silently promoted |
| Prior high-level plan | `Projects/github-portfolio/Plans/05-domain-specific-paddleboard-agent-plan.md` | 6 phases (M1–M6), 31 tasks, risk register R1–R8, parallel lanes — reused and tightened here |
| Repo | — | does not exist; S1 creates it |

**Invariants the build must preserve (from the spec — none may be weakened by any step):**

- **Legal (hard):** fictional brands/models only; every fixture row carries `is_mock: true`; the
  mock-data disclaimer is visible in **both** UI and README. (spec lines 34, 205)
- **Grounding:** every spec/number in an answer traces to that turn's tool results — enforced in
  code, not just the prompt. (spec line 84)
- **Refusal:** out-of-domain → `refused: true`, **zero tools run**. (spec line 85)
- **Typed contracts:** `/api/chat` always returns `ChatResponse`; the model never emits raw
  JSX/HTML/markup — the server assembles payloads, the UI renders them. (spec lines 87–90)
- **Offline determinism:** unit tests and default CI run with a **mocked LLM**; temperature 0;
  deterministic seed data. Live-model calls only in the manually-triggered eval workflow. (spec
  lines 119, 175, 180)
- **Ports:** web 3006, api 8006. (spec line 42)

## 3. Target architecture

```
BEFORE                       AFTER
──────                       ─────
(nothing exists)             sample_data/*.json ─► seed (idempotent) ─► SQLite (boards, accessories, compat_rules)
                                                                             │
                             POST /api/chat ─► refusal backstop ─► LangChain agent (SUP-only system prompt,
                                                │ refused=true,     4 DB-backed tools, ≤6 iterations, temp 0)
                                                │ zero tools            │
                                                │                  grounding validator (code): every spec ∈ tool results
                                                │                       │  else strip → "I don't have that spec"
                                                ▼                       ▼
                             ChatResponse {answer, cards[], tables[], compatibility[], tools_used[], refused, prompt_version}
                                                                        ▼
                             React :3006 ─ product cards, spec tables, compat badges, catalog panel, mock-data banner
                             (nginx serves the static bundle and proxies /api → api:8006)
```

The shape buys a demonstrable anti-hallucination story (constraint → tools → code-level check →
measured evals); it costs a heuristic validator whose edge cases must be tested hard (R1).

## 4. Key design decisions (the real forks — decided before S1)

> Forks 4.1–4.5 carry the spec's `<!-- ASSUMED -->` / "Assumptions I made" markers: they are
> **resolved by default with the assumption noted**, not silently promoted to original decisions.
> Forks 4.6–4.12 are new calls this plan makes. The steps doc copies all of these into "Decisions
> baked in".

### 4.1 Product data — all synthetic, fictional brands (resolved-by-default; spec assumption)
**Decision (2026-07-09):** all brands/models/specs are fictional and mock (Aquara, Riptide, Zephyr,
Cascade, Velocity, Fjord); `is_mock: true` on every row; disclaimer in UI and README.
Why: spec's hard legal constraint — presenting invented specs as real products is the one
unrecoverable failure mode. Trade accepted: less "real-world" flavor. Consequences: a **real-brand
denylist test** ships with the fixtures (S2) and re-runs at the publish gate (S26).

### 4.2 Storage — SQLite seeded from JSON (resolved-by-default; spec assumption)
**Decision:** SQLite via SQLAlchemy 2.0, file-backed, seeded idempotently from `sample_data/*.json`.
Why: zero-config clone-and-run. Trade: single-user concurrency — stated in README as a constraint,
not an oversight. Consequence: **do not build** the Postgres swap (R7).

### 4.3 Product images — generated placeholders (resolved-by-default; spec assumption)
**Decision:** solid-color/gradient SVG placeholders derived from `board_type`; no external image
assets. Consequence: `image_url` points at a local static SVG; no network fetch in tests.

### 4.4 LLM access — OpenAI-compatible, function-calling endpoint via env (resolved-by-default; spec assumption)
**Decision:** provider-agnostic client configured by `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`;
temperature 0; ≤6 tool iterations; never hardcode a provider or key. Consequence: evals report
per-model results at S24; README states which models were validated (R2).

### 4.5 Compatibility model — simplified illustrative fitment (resolved-by-default; spec assumption)
**Decision:** the four rule families (fin-box match; pump `max_psi ≥ recommended_psi` + valve match;
leash-by-use; paddle-by-rider-height) are the whole fitment model — not a real gear database.

### 4.6 Compat rules: code vs data — **logic in code, exceptions as data**
**Decision (2026-07-09):** the four rule families live as typed logic in `check_compatibility`
(readable, unit-testable); the `compat_rules` table stores only explicit pair overrides/caveats
seeded from `accessories.json` (gives the seeded incompatible pairings somewhere honest to live).
Why: rules-as-data for four families is over-engineering; a table of exceptions keeps fixtures
expressive. Trade: adding a fifth rule family means code, not data — acceptable for a demo.

### 4.7 Python packaging — `pyproject.toml`, pip, pinned versions
**Decision:** single `backend/pyproject.toml` with `[project.optional-dependencies] dev` (ruff,
black, mypy, pytest, httpx); install via `pip install -e ".[dev]"`; Python 3.11 pinned in
`requires-python` and the Dockerfile. Why: the spec offers "pyproject.toml or requirements.txt" —
one file beats three. Consequence: CI and every Verify block use this exact install line.

### 4.8 Contract freeze — `schemas.py` is the single source; TS types hand-mirrored at S14
**Decision:** Pydantic models in `backend/app/schemas.py` freeze at the end of S4; `frontend/src/
lib/types.ts` mirrors them by hand; **any later schema change must touch both files in one step**
(no such step is planned). Why: codegen (e.g. datamodel-code-generator) is more moving parts than a
demo needs. Trade: drift risk (R8) — mitigated by contract-shape tests on both sides (S7, S15).

### 4.9 Mocked LLM for tests — canned tool-call transcripts via injected fake model
**Decision:** the agent takes its chat-model client by injection; tests inject a fake
OpenAI-compatible model that replays canned tool-call transcripts (LangChain fake-message model or
equivalent). No network, no key, fully deterministic. Consequence: the two signature tests (S12)
and the offline eval mode (S19) both ride this seam.

### 4.10 Refusal backstop — deterministic heuristic classifier, biased to false-refusal
**Decision:** a lightweight keyword/pattern in-domain check (no embeddings, no extra model call)
short-circuits off-topic questions before the agent runs. Policy: prefer false-refusals over
off-topic answers; measure the rate in evals (R3). Why: cheap, deterministic, testable offline.

### 4.11 Frontend serving — nginx static bundle, `/api` proxied to the api service
**Decision:** multi-stage frontend Dockerfile builds the Vite bundle and serves it with
nginx-alpine on 3006, proxying `/api` to `api:8006`. Why: avoids CORS config and a second origin;
matches "static bundle behind a lightweight server". Consequence: dev mode uses Vite's own proxy
with the same path contract.

### 4.12 Playwright smoke — offline via route interception
**Decision:** the one Playwright test mocks `/api/*` responses with route interception (fixture
payloads from the frozen contract), so E2E runs in default CI with no backend and no key. Why:
keeps CI free and deterministic (R5); the live end-to-end proof happens at gate S23 instead.

## 5. Protocol / interface changes

Greenfield: these are **new contracts, frozen at S4** — every later step builds against them, none
may change them (a change would re-open S4 + S14 together, per §4.8).

- **`POST /api/chat`** `{message, history?}` → `ChatResponse { answer: str, cards: list[BoardCard],
  tables: list[SpecTable], compatibility: list[CompatibilityResult], tools_used: list[ToolCall],
  refused: bool, prompt_version: str }`.
- **`GET /api/boards`** (query filters: type, skill, max weight, price, length; paginated) →
  `list[BoardCard]`; **`GET /api/boards/{id}`** → `BoardCard`.
- **`GET /api/health`**, **`GET /api/metrics`** (request count, p50/p95 latency, refusal rate, avg
  tools/turn).
- Supporting types: `SpecTable {title, columns, rows, board_ids}`, `CompatibilityResult {board_id,
  accessory_id, compatible, reason, caveats}`, `ToolCall {name, args, result_summary, latency_ms}`.
- **Backward-compat behavior:** `history` optional (absent ⇒ single-turn); unknown query filters
  ignored; the model never emits markup — the server assembles all structured payloads.

## 6. Phased plan (P1 … P6)

Ordering invariant: **everything offline-verifiable lands first (P1–P5, one unattended segment);
anything paid, live, human-judged, or externally visible is last (P6, gated)**. Greenfield has no
destructive steps and no flags — "ships dark" reduces to: nothing is public until S26.

### P1 — Data foundation (S1–S4)
Repo scaffold + prescribed tooling, fixtures with the real-brand denylist, models + idempotent
seeder, frozen Pydantic contracts. **Acceptance:** `pytest -q` green; seeding twice yields
identical row counts; `ruff`/`black`/`mypy` clean.

### P2 — Deterministic core (S5–S7)
The four tools as plain DB-backed Python + the catalog API. No LLM anywhere. **Acceptance:** tool
and endpoint tests green offline; `curl :8006/api/boards?skill_level=beginner` returns seeded JSON.

### P3 — Constrained agent (S8–S13)
Versioned prompts, grounding validator (pure function, built before the agent exists), refusal
backstop, injected-model agent, `/api/chat` pipeline, observability. **Acceptance:** both signature
tests (no-ungrounded-spec; zero-tool refusal) green with the mocked LLM.

### P4 — Consumer UI (S14–S18) — runs in parallel with P2/P3 after S4
Vite scaffold with the spec's visual identity, structured renderers, chat pane, catalog panel +
mock-data banner, offline Playwright smoke. **Acceptance:** `vitest run`, `tsc --noEmit`,
`eslint`, `playwright test` all green with mocked API.

### P5 — Rigor & packaging (S19–S22)
Offline eval harness + example prompts, Docker packaging, CI workflows (offline default + manual
paid eval workflow), README draft with placeholders for GIF + live-eval table. **Acceptance:**
`make eval` prints the correctness/grounding/refusal table offline; `docker compose build` exits 0
and `up -d` passes health curls; all CI commands pass locally.

### P6 — Validate, prove, ship (S23–S26; **every step gated, LAST**)
S23 live smoke with a real key (**human + paid**, written go/no-go) → S24 live-model eval runs
(**paid**) → S25 demo GIF + README finalization (**human**) → S26 publish to GitHub, CI green
remotely, DoD walk (**human; externally visible**). **Acceptance:** the spec's Definition-of-done
checklist, 100% with fresh evidence.

## 7. Decommission / cleanup checklist

Dropped — greenfield build; nothing exists to remove. (The only deletion anywhere is
`docker compose down -v` in verify blocks, which removes scratch containers/volumes the step itself
created.)

## 8. Rule & doc updates (keep the docs truthful)

- `README.md` (repo): stub with mock-data disclaimer from S1; full portfolio README at S22;
  finalized (GIF + live-eval numbers) at S25. The disclaimer may never be removed.
- `backend/app/prompts/README.md` (S8): documents the domain constraint, grounding guardrail, and
  refusal backstop — updated in the same commit as any prompt change.
- `docs/SPEC.md` (S1): frozen copy of the build brief; never edited by workers.
- Vault: `domain-specific-paddleboard-agent-progress.md` is updated after every step (the only
  vault file the run writes); this plan's Status header advances PROPOSED → IN PROGRESS (S\<k\>) → DONE.

## 9. Privacy / security / compatibility impact

- **No real user data** anywhere: sessions ephemeral, no accounts, no persistence of chat history.
- **Secrets:** `LLM_API_KEY` via env only; `.env` gitignored; `.env.example` documents variables
  with placeholder values; the CI eval workflow reads a GitHub Actions secret. A secret-scan grep is
  part of the S26 publish verify.
- **Trust boundary:** the grounding validator and refusal backstop sit server-side on
  `/api/chat` — the one boundary where model output meets the user. Nothing model-generated is
  rendered as markup (typed payloads only).
- **Legal:** fictional brands enforced by the S2 denylist test, re-verified at S26 before anything
  becomes public.

## 10. Risks & rollback

Rollback is uniform until P6: every step is additive on a per-step branch — a failed step is
discarded without unwinding others; nothing is public, paid, or destructive before S23.

| # | Risk | Mitigation / rollback |
|---|---|---|
| R1 | **Grounding validator false positives** (kg↔lbs, "about 150 L", summed prices strip legitimate content) — the project's core claim | Validator is a pure LLM-free function (S9) so edge cases are cheap unit tests; normalize units + tolerance bands; dedicated eval cases (S19). Caught at S9/S12/S19 verifies. Backout: fix in-step; never weaken the invariant. |
| R2 | **Provider variance in tool calling** (local models unreliable) | Mocked LLM everywhere offline; live behavior measured per-model at S24 (gated); README names validated models. Backout: report the model as unsupported rather than degrading the guardrail. |
| R3 | **Refusal backstop misfires** (borderline: "water temperature for paddling?") | Policy fixed in §4.10: prefer false-refusal; measure rate in evals; keep the classifier simple and documented. |
| R4 | **Legal/trademark failure** — the one unrecoverable failure for a public repo | Denylist test at S2; `is_mock: true` on every row; disclaimer from S1 (README) + S17 (UI banner); re-grep at S26 before publish. Backout before S26 is free (nothing public). |
| R5 | **Paid calls leak into default CI** | All unit tests use the injected fake model (§4.9); Playwright mocks the API (§4.12); the eval workflow is separate, manual, secret-gated (S21). Caught by S21 verify (default CI runs with no key present). |
| R6 | **Scope creep** (stretch goals, commerce-shaped features) | §1 non-goals are contractual; stretch goals start only after S26 as new work; step prompts forbid out-of-step changes. |
| R7 | **SQLite concurrency questioned by reviewers** | Stated constraint in README (§4.2); do not build the swap. |
| R8 | **FE/BE contract drift while lanes run in parallel** | Contracts freeze at S4 (§4.8); shape tests on both sides (S7, S15); no planned step edits `schemas.py` after S4. |
| R9 | **Unattended-run cost blowout** (26 steps × worker+reviewer subagents) | Workflow doc mandates a shakeout slice (S1–S4) to gauge spend before launching the rest; `/workflows` shows per-subagent tokens; `x` stops without losing merged steps. |

## 11. Acceptance criteria (whole change — from the spec's Definition of done)

- [ ] `docker compose up` serves UI on `:3006`, API on `:8006`; catalog seeded; ≥3 example prompts
      return grounded product cards and/or a comparison table (live proof at S23).
- [ ] Every spec in an answer traces to a tool result; the no-ungrounded-spec test passes; the
      agent says "I don't have that spec" when the DB lacks it.
- [ ] Off-topic questions refused with zero tools run; the refusal test passes.
- [ ] Every `/api/chat` response is a typed `ChatResponse`; UI renders cards/tables/badges from the
      structured payload — never raw model text.
- [ ] `check_compatibility` passes and fails the seeded pairings correctly; badges color-map
      green/red/amber.
- [ ] `make eval` prints the correctness / grounding / refusal table (offline; live numbers at S24).
- [ ] CI green (locally at S21, remotely at S26); README renders with working GIF + Mermaid; the
      mock-data disclaimer is visible in **both** UI and README.

## 12. Implementation map

- **Repo scaffold & tooling**: root files, `backend/pyproject.toml`, `Makefile`, `.env.example`,
  `docs/SPEC.md` — S1.
- **Data**: `sample_data/*.json` — S2; `backend/app/db/{models,session,seed}.py` — S3;
  `backend/app/schemas.py` — S4.
- **Core logic**: `backend/app/agent/tools.py` — S5–S6; `backend/app/main.py` (catalog) — S7.
- **Agent & guardrails**: `backend/app/prompts/` — S8; `backend/app/agent/guardrails.py` — S9–S10;
  `backend/app/agent/agent.py` — S11; chat pipeline in `main.py` — S12;
  `backend/app/observability.py` — S13.
- **Frontend**: `frontend/` scaffold + `src/lib/` — S14; `src/components/` — S15–S17;
  `e2e/` — S18.
- **Proof & packaging**: `evals/`, `sample_data/example_prompts.md` — S19; Dockerfiles +
  `docker-compose.yml` — S20; `.github/workflows/` — S21; `README.md` — S22.
- **Gated**: live smoke — S23; live evals — S24; GIF + README final — S25; publish + DoD — S26.

Sources (verified in-vault 2026-07-09):
`Projects/github-portfolio/05-domain-specific-paddleboard-agent.md` (authoritative spec, incl. its
ASSUMED markers), `Projects/github-portfolio/Plans/05-domain-specific-paddleboard-agent-plan.md`
(prior plan: phases, risk register, parallel lanes). No repo exists to cite.
