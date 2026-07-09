---
type: workflow-driver
tags: [github-portfolio, boardwise, llm-agent, migration-orchestration, dynamic-workflow]
project: "[[05-domain-specific-paddleboard-agent]]"
slug: domain-specific-paddleboard-agent
status: ready
created: 2026-07-09
---

# BoardWise (Project 05) — Dynamic-Workflow Driver

**Driver decision (final):** Claude Code **dynamic workflow** — this greenfield build is
gate-light (all four gates sit at the very end) and its dependency graph has three long independent
lanes (backend core, guardrails, frontend), which is exactly where native workflow parallelism
beats a serial orchestrator. Requires Claude Code v2.1.154+, a paid plan, and the
Dynamic-workflows opt-in in `/config`.

You do **not** hand-write the workflow script. You paste the segment brief below after
`ultracode:`; the runtime writes the script, shows the planned phases for approval, runs the
worker→reviewer→fix loop in the background, and can save the script to `.claude/workflows/` as a
rerunnable command.

**Executes:** `domain-specific-paddleboard-agent-implementation-steps.md` (S1–S26).
**Why:** `domain-specific-paddleboard-agent-plan.md`.
**Durable state:** `domain-specific-paddleboard-agent-progress.md` — the cross-session source of
truth; a subagent appends to it after every merged step.
**Repo root:** `~/workspace/boardwise` (S1 creates it; override via `args`).
**Integration branch:** `main` (fresh repo — trunk is the integration branch); per-step branches
`s<NN>-<short>`.

## The two constraints that shape the run

A workflow cannot pause for human input mid-run, and its script has no direct filesystem/shell
access — only subagents read, write, build, test, and commit. Therefore:

- **Every gate is a WORKFLOW BOUNDARY.** S23 (human+paid live smoke), S24 (paid evals), S25 (human
  GIF capture), S26 (human publish) are never inside an unattended run.
- **Nothing paid, live, or externally visible runs inside Segment 1.** All S1–S22 verifies are
  offline (unset `LLM_API_KEY` proves it); package installs and `docker compose build` are the
  only network activity.

## Segments (cut at every gate)

```
Steps:    S1 ──────────────────────────────── S22 │ S23        │ S24       │ S25 → S26
Segments: └────────── SEGMENT 1 (workflow) ───────┘  (human+paid) (paid)      └ SEGMENT 4 ┘
                                                     SEGMENT 2    SEGMENT 3   (human, publish)
```

| Segment | Steps | Nature | Launch |
|---|---|---|---|
| 1 | S1–S22 | fully offline build; max parallelism | `ultracode:` brief below — **after the shakeout slice** (see cost note) |
| 2 | S23 | live smoke — **HUMAN sign-off + PAID** (real key, ~cents) | manual, or a single-step supervised run; written GO/NO-GO into the progress file |
| 3 | S24 | live-model eval runs — **PAID**, per-provider "go" | manual `python evals/run_evals.py --mode live` per provider, or one small gated workflow |
| 4 | S25–S26 | GIF capture (human hands) + publish to GitHub (**externally visible**) | manual; S26's pre-publish greps are non-negotiable |

**Cost shakeout (plan R9):** before launching all of Segment 1, run a first mini-workflow on
**S1–S4 only** with the same brief (set the step range in `args`). Check `/workflows` per-subagent
token spend, then launch S5–S22 as the remainder. Both runs use the same progress file, so nothing
is lost between them.

## Segment 1 brief (paste after `ultracode:`)

```
Read, in order: /Users/zen/Documents/Claude/Projects/github-portfolio/Plans/05-domain-specific-paddleboard-agent/domain-specific-paddleboard-agent-plan.md
(the why — especially §0 prescribed conventions and §4 decisions),
domain-specific-paddleboard-agent-implementation-steps.md (the script — steps S1..S22 with prompts
and Verify blocks), and domain-specific-paddleboard-agent-progress.md (durable state — skip any
step already `passed`). Repo root: ~/workspace/boardwise (S1 creates it if absent; after S1, all work
happens inside it and docs/SPEC.md is the in-repo spec).

Drive steps S1–S22 as a DAG using the steps doc's dependency graph — respect the sequence, exploit
the parallelism:
- A step is ELIGIBLE when all its prerequisites are `passed` in the progress file.
- Run eligible steps with DISJOINT "Edits" file sets in parallel, each on its own branch
  s<NN>-<short> off main — the frontend lane (S14–S18), guardrails (S9–S10), and backend core
  (S5–S7) should overlap. Keep effective fan-out well under 16 (each step also spawns a reviewer
  and up to 3 fixers).
- SERIALIZE steps joined by an edge and any two steps whose Edits share a file
  (S5→S6 tools.py; S9→S10 guardrails.py; S7→S12→S13 main.py; S16→S17 App.tsx).

Per step:
1. WORKER subagent: implement ONLY this step from its fenced prompt in the steps doc; obey the
   "Project rules every prompt must respect"; RUN the step's Verify block and capture actual
   output; commit on the step branch with Conventional Commits, staging files by name.
2. REVIEWER subagent (fresh) on the branch diff with this inline checklist:
   (a) correctness vs the step's Goal — nothing more, nothing less (no scope creep, no stretch
       goals); (b) the frozen contract untouched — after S4, app/schemas.py must not change; after
       S14, src/lib/types.ts must not change; (c) legal invariant — fictional brands only,
       is_mock true, mock-data disclaimer intact; (d) offline invariant — no test or default-CI
       path makes a network LLM call or needs a key; no secrets in source; (e) grounding/refusal
       invariants not weakened to make a check pass; (f) the Verify output pasted by the worker is
       real, complete, and matches the block's expected results; (g) tests adequate for the Goal.
   Return VERDICT: PASS or CHANGES_REQUESTED with numbered file:line issues; do not fix.
3. FIX loop: on CHANGES_REQUESTED a fresh subagent addresses the issues, re-runs Verify,
   re-reviews. Cap 3 cycles, then mark the step `blocked` in the progress file, stop its lane, and
   continue independent lanes.
4. On PASS: merge the step branch into main (no force-push), then a subagent updates
   domain-specific-paddleboard-agent-progress.md: status row (passed, attempts, branch, merge SHA,
   one-line note incl. any CARRY-FORWARD) + an append-only Log line.

HARD STOPS: never start a step whose prerequisites are not `passed`; never skip or weaken a
Verify; never touch S23–S26 (they are gated human/paid segments); never make a live LLM call or
read LLM_API_KEY; never edit files under /Users/zen/Documents/Claude except the progress file.
Finish by surfacing: steps passed/blocked, total attempts, and the exact next action (Segment 2 =
gated S23 live smoke — requires human go + a real key).
```

`args` parameterization for reruns: `{ "repo_root": "~/workspace/boardwise", "steps": "S1..S22" }` —
pass `"steps": "S1..S4"` for the shakeout slice, `"S5..S22"` for the remainder, or a single step
id to retry one that was `blocked`.

## Segments 2–4 (gated — run supervised, not unattended)

- **Segment 2 (S23):** human sets a real key in `.env`, brings the compose stack up, walks the five
  scripted scenarios from the steps doc, records the written GO/NO-GO in the progress file. May be
  run as a single-step workflow, but the sign-off itself is always human.
- **Segment 3 (S24):** one explicit "go" per provider; run the live evals, paste per-model tables
  into README, commit captures under `evals/results/`.
- **Segment 4 (S25–S26):** S25 is human screen-capture work. S26 publishes: pre-publish denylist +
  secret greps first, then `gh repo create` + push + remote CI green + the DoD walk. Externally
  visible — explicit "go" required.

## Runtime behavior & limits (applied to this run)

| Documented behavior | Applied here |
|---|---|
| No mid-run user input | 4 gates = 3 boundaries after S22; Segment 1 contains zero gates by construction |
| Script has no FS/shell | every Verify is run by the step's worker subagent and its output pasted for the reviewer |
| Subagents inherit your allowlist; non-allowlisted calls can stall a run | pre-add the allowlist below before launching Segment 1 |
| ≤16 concurrent subagents, ≤1000/run | max width in the graph is ~4 parallel steps × (worker+reviewer) — comfortably under the cap; keep it there |
| Resumable in-session only | `domain-specific-paddleboard-agent-progress.md` is the cross-session memory; a fresh session relaunches the brief and skips `passed` rows |
| Cost scales with subagent count | S1–S4 shakeout first (plan R9); `/workflows` for per-subagent tokens; `x` stops without losing merged steps |

## Pre-add to the permission allowlist (so Segment 1 never stalls)

```
git init / add / commit / checkout / merge / branch / log / diff / status
python3.11 -m venv ; pip install -e ".[dev]" ; pytest ; ruff ; black ; mypy
python -m app.db.seed ; python evals/run_evals.py ; sqlite3 ; make
npm ci / run / install ; npx tsc ; npx vitest ; npx eslint ; npx playwright
uvicorn ; curl ; docker compose (build / up / down / exec)
mkdir ; cp ; diff ; grep ; test ; rm (scratch files only)
```

(Do **not** allowlist `gh repo create` / `git push` — those belong to gated S26 only.)

## Done-when (this driver doc is finished)

- [x] Segments drawn, with every gate (S23 human+paid, S24 paid, S25 human, S26 human/public) as a
      boundary — none inside an unattended run.
- [x] Reusable Segment-1 brief written, with the inline reviewer checklist filled in.
- [x] Allowlist of build/test/git commands listed for pre-adding.
- [x] `domain-specific-paddleboard-agent-progress.md` named as the cross-session source of truth
      the workflow updates per step.
