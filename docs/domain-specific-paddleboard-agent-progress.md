---
type: progress-tracker
tags: [github-portfolio, boardwise, llm-agent, migration-orchestration, durable-state]
project: "[[05-domain-specific-paddleboard-agent]]"
slug: domain-specific-paddleboard-agent
status: pending
created: 2026-07-09
---

# BoardWise (Project 05) — Orchestration Progress

**Durable state for the driver.** On start/resume, READ this file to know where you are.
Source script: `domain-specific-paddleboard-agent-implementation-steps.md` (S1..S26).
Repo root: `/Users/zen/workspace/boardwise` (override of the doc's default `~/workspace/boardwise` —
this is the environment's designated working directory, already `git init`'d with the planning
docs present) · Integration branch: `main` · Per-step branches: `s<NN>-<short>`.
Review routing: fresh reviewer subagent per step with the inline checklist from
`domain-specific-paddleboard-agent-workflow.md` Segment-1 brief (greenfield — no repo review
agents exist).

## Rules in force

- Respect the dependency graph: start a step only when its prerequisites are `passed`; run
  independent steps (disjoint Edits file sets, no edge) in parallel; never let two steps edit the
  same file concurrently (serialized pairs: S5→S6 `tools.py`, S9→S10 `guardrails.py`,
  S7→S12→S13 `main.py`, S16→S17 `App.tsx`).
- Cap 3 review cycles per step → else mark `blocked`, stop that lane, surface a summary.
- STOP at every gate; require an explicit written "go":
  **S23 = HUMAN sign-off + PAID (live smoke, real API key). S24 = PAID (live-model evals, per
  provider). S25 = HUMAN (manual GIF capture). S26 = HUMAN + externally visible (public GitHub
  publish).**
- Never auto-run paid/live operations: no live LLM call and no `LLM_API_KEY` anywhere in Segment 1
  (S1–S22); no `git push` / `gh repo create` before S26's go.
- Contract freeze: after S4 no step edits `backend/app/schemas.py`; after S14 no step edits
  `frontend/src/lib/types.ts`.
- Legal invariant: fictional brands only; `is_mock: true`; mock-data disclaimer never removed
  (denylist grep re-runs at S26).
- The only vault file the run writes is this one.

## ⚠️ Deferred verification gate (runs at the gated segments, never unattended)

- S23: full live end-to-end — 5 scripted scenarios on a real model (grounded cards, SpecTable,
  compat badge, "I don't have that spec", zero-tool refusal) + `/api/metrics` spot-check. Proves
  the change WORKS, not just that offline tests pass.
- S24: `python evals/run_evals.py --mode live` per provider — the real
  correctness/grounding/refusal numbers for the README.
- S26: remote CI green on GitHub (`gh run list … ci.yml` → `completed success`) — ci.yml commands
  were only proven locally at S21 because no remote existed.
- S26: pre-publish real-brand denylist grep + secret-scan grep — both must return nothing.

## Status table

| Step | Title | Status | Attempts | Branch | Commit SHA | Note |
|------|-------|--------|----------|--------|-----------|------|
| S1 | Scaffold repo, tooling, spec copy | pending | 0 | — | — | |
| S2 | Fixtures + real-brand denylist test | pending | 0 | — | — | |
| S3 | SQLAlchemy models + idempotent seeder | pending | 0 | — | — | |
| S4 | Freeze Pydantic contracts | pending | 0 | — | — | contract freeze: schemas.py locked after this |
| S5 | Tools: get_board + search_boards | pending | 0 | — | — | |
| S6 | Tools: check_compatibility + recommend_setup | pending | 0 | — | — | same file as S5 — serialized |
| S7 | Catalog API (/api/boards, /api/health) | pending | 0 | — | — | |
| S8 | Versioned prompts as assets | pending | 0 | — | — | |
| S9 | Grounding validator (pure function) | pending | 0 | — | — | highest-risk step (plan R1) |
| S10 | Refusal backstop | pending | 0 | — | — | same file as S9 — serialized |
| S11 | Constrained LangChain agent (injected model) | pending | 0 | — | — | |
| S12 | /api/chat pipeline + signature tests | pending | 0 | — | — | |
| S13 | Observability + /api/metrics | pending | 0 | — | — | |
| S14 | Frontend scaffold + mirrored types | pending | 0 | — | — | types.ts locked after this |
| S15 | Renderers: ProductCard/SpecTable/CompatBadge/RefusalCard | pending | 0 | — | — | |
| S16 | Chat pane + composer + example chips | pending | 0 | — | — | |
| S17 | Catalog panel + mock-data banner | pending | 0 | — | — | same file (App.tsx) as S16 — serialized |
| S18 | Offline Playwright smoke | pending | 0 | — | — | |
| S19 | Eval harness (offline) + example prompts | pending | 0 | — | — | |
| S20 | Docker packaging (web 3006 / api 8006) | pending | 0 | — | — | |
| S21 | CI workflows (offline default + manual evals) | pending | 0 | — | — | remote green deferred to S26 |
| S22 | Portfolio README draft (TODO markers) | pending | 0 | — | — | |
| S23 | Live smoke — GATE: HUMAN + PAID | pending | 0 | — | — | written GO/NO-GO required here |
| S24 | Live-model eval runs — GATE: PAID | pending | 0 | — | — | one go per provider |
| S25 | Demo GIF + README final — GATE: HUMAN | pending | 0 | — | — | manual capture |
| S26 | Publish + remote CI + DoD walk — GATE: HUMAN, public | pending | 0 | — | — | denylist + secret grep first |

> Status values: pending | in_progress | passed | blocked. The Note is one line: review outcome,
> test count, any CARRY-FORWARD for a later step, and why a blocked step is blocked.

## Dependency graph

```
Phase A (foundation)   S1 → S2 → S3 ;  S1 → S4 ;  S1 → S8
Phase B (core)         (S3,S4) → S5 → S6 ;  (S4,S5) → S7
Phase C (agent)        S4 → S9 → S10 ;  (S6,S8) → S11 ;  (S7,S10,S11) → S12 → S13
Phase D (frontend)     S4 → S14 → S15 → S16 → S17 → S18
Phase E (proof)        S12 → S19 ;  (S7,S17) → S20 ;  (S13,S18,S19,S20) → S21 ;  (S19,S20) → S22
Phase F (gated, LAST)  (S21,S22) → S23(HUMAN+PAID) → S24(PAID) → S25(HUMAN) → S26(HUMAN, publish)
```

Segments: 1 = S1–S22 (unattended workflow; shakeout slice S1–S4 first per plan R9) · 2 = S23 ·
3 = S24 · 4 = S25–S26.

## Log

> Append-only. One line per state change: what passed/blocked, merge SHA, what's next.

- 2026-07-09: SETUP done. Four docs written (plan / steps / workflow / progress), S1–S26 seeded
  pending. Repo does not exist yet — S1 creates `~/workspace/boardwise`. Next: launch Segment-1
  shakeout slice (S1–S4) per the workflow doc's brief.
- 2026-07-09: SETUP corrected. Actual repo root is `/Users/zen/workspace/boardwise` (already
  `git init`'d, unborn `master`, docs/ untracked) — not `~/workspace/boardwise` as the stale entry
  above assumed; steps doc explicitly allows overriding repo root. Renamed unborn branch
  `master` → `main` via `git symbolic-ref HEAD refs/heads/main` (safe: zero commits existed).
  Confirmed SPEC source exists at
  `/Users/zen/Documents/Claude/Projects/github-portfolio/05-domain-specific-paddleboard-agent.md`
  and `python3.11` resolves (3.11.14). Every worker/reviewer dispatch for this run substitutes
  `/Users/zen/workspace/boardwise` for `~/workspace/boardwise` in step prompts. Next: dispatch S1
  worker.
