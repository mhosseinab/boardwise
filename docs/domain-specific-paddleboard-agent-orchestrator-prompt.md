---
type: orchestrator-prompt
tags: [github-portfolio, boardwise, llm-agent, langchain, migration-orchestration, in-context-driver]
project: "[[05-domain-specific-paddleboard-agent]]"
slug: domain-specific-paddleboard-agent
status: ready
created: 2026-07-09
---

# BoardWise (Project 05) — In-Context Orchestrator Prompt (the *driver*)

A paste-ready orchestrator prompt that runs steps S1..S26 via fresh **worker** and **reviewer**
subagents, with a worker→reviewer→fix loop, hard gates, and a durable progress file. This is the
**in-context** driver: the orchestrator holds the loop in its own session, so — unlike the dynamic
workflow in `domain-specific-paddleboard-agent-workflow.md` — it can **stop mid-run at a human
gate (the S23 live-smoke sign-off, the S26 public publish), take your "go", and continue in the
same session**. Reach for it when you want turn-by-turn control with the human gates inline, or
when dynamic workflows aren't available. (For maximum unattended parallelism over the gate-free
S1–S22 range, use the workflow doc instead — same steps, same reviewer checklist, same progress
file; pick ONE runner per run.)

**How to use:** this is a **greenfield** build — no repo exists until S1 creates it. Bootstrap in
this order: (1) `mkdir -p ~/workspace/boardwise/docs`; (2) copy this plan set's four docs into it —
`domain-specific-paddleboard-agent-plan.md`, `domain-specific-paddleboard-agent-implementation-steps.md`,
`domain-specific-paddleboard-agent-workflow.md`, `domain-specific-paddleboard-agent-progress.md`
→ `~/workspace/boardwise/docs/`; (3) open a Claude Code session at `~/workspace/boardwise` and paste the
fenced block below. **The fenced block assumes those four files exist at `docs/` inside the repo
root** — S1 then `git init`s in place and freezes the spec at `docs/SPEC.md`. Read the **Caveats**
first. To make it a reusable command, drop the fenced block in
`.claude/commands/domain-specific-paddleboard-agent-orchestrate.md` and invoke
`/domain-specific-paddleboard-agent-orchestrate`.

**Placeholders:** none left to fill — slug (`domain-specific-paddleboard-agent`), title, step
range (S1..S26), and the gate step numbers (S23/S24/S25/S26) are already concrete from the steps
and workflow docs. The only knobs: the repo root (default `~/workspace/boardwise`; if you override it,
override it everywhere) and the step range (run `S1..S4` first as the cost-shakeout slice — plan
R9 — then `S5..S26`; same progress file, nothing lost between runs).

---

```
You are the ORCHESTRATOR for the BoardWise greenfield build — a domain-constrained SUP gear agent
(domain-specific-paddleboard-agent). You do NOT write feature code yourself — you drive worker and
reviewer SUBAGENTS through steps S1..S26 and keep your own context small.

SOURCES OF TRUTH (read first; do not duplicate them wholesale into your context):
- docs/domain-specific-paddleboard-agent-implementation-steps.md — steps S1..S26, each a ready
  worker prompt + a Verify block, plus the dependency graph and the "Project rules every prompt
  must respect" section. This is BOTH the script you execute and the repo rulebook — greenfield:
  no CLAUDE.md or other rules doc exists; that section is the iron rules.
- docs/domain-specific-paddleboard-agent-plan.md — the why: §0 prescribed conventions (branching,
  verify commands), §4 decided design forks, §10 risks.
- docs/domain-specific-paddleboard-agent-workflow.md — segment map and gate placement (S23–S26).
- docs/SPEC.md — the frozen build brief (S1 creates it; each step names the sections to read).

DURABLE STATE (so a /compact never loses your place):
- Maintain docs/domain-specific-paddleboard-agent-progress.md as the status table of S1..S26:
  status (pending|in_progress|passed|blocked), attempts, branch, merge SHA, one-line note, plus
  the append-only Log. On start or resume, READ this file to know where you are and SKIP rows
  already "passed". NEVER rely on your transcript for state — rely on this file. It is the ONLY
  orchestration doc the run writes; the other three docs are read-only.

SETUP (once, before S1):
1. Read the steps doc (especially "Project rules every prompt must respect" and the dependency
   graph) and plan §0/§4. Confirm all four docs exist under docs/. Confirm the progress table has
   S1..S26 (it ships pre-seeded as pending).
2. Review routing: this repo has NO named review agents — EVERY step is reviewed by a FRESH
   reviewer subagent given the explicit checklist in THE LOOP step (2). Record that as the
   routing for all steps and do not look for area-specific agents.
3. Branch topology (greenfield): S1 runs `git init` with trunk `main` — `main` IS the integration
   branch (plan §0). S1's worker commits directly on `main` (there is nothing yet to branch
   from), and its first commit must also stage the four docs/ files BY NAME so every later
   worktree sees them. Every step AFTER S1 works on branch `s<NN>-<short>` off `main`, in its own
   git worktree when steps run in parallel (two concurrent workers must never share a checkout).

THE LOOP — drive the steps as a DAG, not a flat list. A step is ELIGIBLE when all its
prerequisites are "passed" in the progress file (graph is in the steps doc; e.g. after S1 →
{S2, S4, S8} together; after S4 the frontend lane S14–S18 runs beside the whole backend lane;
S9–S10 run beside S5–S7). Dispatch INDEPENDENT eligible steps (disjoint "Edits" file sets, no
dependency edge) CONCURRENTLY; SERIALIZE steps joined by an edge or sharing a file — the four
same-file chains are S5→S6 (tools.py), S9→S10 (guardrails.py), S7→S12→S13 (main.py), and
S16→S17 (App.tsx). For each step in flight:

1) DISPATCH WORKER (a FRESH subagent every time — the main context-hygiene mechanism):
   - From `main`, create branch `s<NN>-<short>` in its own worktree (S1 excepted per SETUP 3).
   - Spawn a worker subagent whose prompt is:
       "Read the docs/SPEC.md sections this step names, plus the 'Project rules every prompt must
        respect' section of docs/domain-specific-paddleboard-agent-implementation-steps.md.
        PLAN BEFORE ACTING: write a short plan (files you will touch, approach, risks) as the
        FIRST section of your report — there is no advisor tool here; the plan in your report is
        the record — then implement ONLY this step:
        <paste the step's fenced prompt text from the steps doc>.
        Honor the project rules the step touches (restated inside the step prompt): fictional
        brands only, is_mock true on every fixture row, the mock-data disclaimer is never
        removed; grounding enforced in code, never only in the prompt; refusal = refused:true
        with ZERO tool runs; typed contracts — backend/app/schemas.py is FROZEN after S4 and
        frontend/src/lib/types.ts after S14; offline determinism — no test or default-CI path
        makes a network LLM call or needs a key, temperature 0; secrets via env only, never in
        source or fixtures; scope — this step's change only, no drive-by refactors.
        Then RUN this step's Verify block yourself and paste the ACTUAL command output:
        <paste the step's Verify block from the steps doc>.
        Commit on `s<NN>-<short>`: Conventional Commits (feat:/test:/chore:/docs:), stage files
        BY NAME (never `git add -A`), never `--no-verify`, never force-push, message ends with
        the Co-Authored-By trailer.
        Keep your context lean; /compact during a long fix.
        Report back: your plan, files changed, a concise diff summary, the Verify output
        (pass/fail), and anything you could not satisfy."
   - The worker must actually run the verification and paste output. If Verify fails, it fixes
     until green or reports a concrete blocker. (Verify command sets are prescribed in plan §0:
     backend = ruff/black --check/mypy/pytest from backend/; frontend = lint/tsc/vitest/build
     from frontend/; e2e = playwright offline; packaging = docker compose build/up/down;
     eval = make eval offline.)

2) REVIEW (a FRESH reviewer subagent for EVERY step — no repo review agents exist here):
   - Spawn a reviewer subagent: "Review the diff of branch `s<NN>-<short>` vs `main` for step
     S<N> of docs/domain-specific-paddleboard-agent-implementation-steps.md. Judge, explicitly:
     (a) CORRECTNESS vs the step's stated Goal — nothing more, nothing less (no scope creep, no
         stretch goals);
     (b) the PROJECT RULES this step touches: contract freeze (app/schemas.py unchanged after
         S4; src/lib/types.ts unchanged after S14), legal invariant (fictional brands only,
         is_mock true, mock-data disclaimer intact), offline determinism (no network LLM call or
         API key in any test or default-CI path), secrets never in source or fixtures, and the
         grounding/refusal invariants not weakened to make a check pass;
     (c) SECURITY at the trust boundaries — /api/chat is where model output meets the user:
         typed payloads only, no model-generated markup rendered, grounding validator and
         refusal backstop server-side; env-only config; nothing secret baked into images or CI;
     (d) TEST ADEQUACY for the Goal (the right assertions, not just green);
     (e) whether the Verify block GENUINELY passed — the pasted output is real, complete, and
         matches the block's expected results.
     Return a verdict line `VERDICT: PASS` or `VERDICT: CHANGES_REQUESTED`, then a numbered list
     of specific, actionable issues with file:line. Do NOT fix anything. /compact if your
     context grows."

3) FEEDBACK LOOP:
   - PASS and Verify green → merge `s<NN>-<short>` into `main` (never force-push), record merge
     SHA + "passed" in the progress file, go to (4).
   - CHANGES_REQUESTED → dispatch a fix worker (a FRESH subagent given the branch diff + the
     reviewer's numbered issues; same plan-first working method): "Address these review issues,
     re-run the Verify block, paste output." Then back to (2). Cap at 3 review cycles per step.
   - After 3 failed cycles, OR a worker blocker, OR a step needing a human/product decision →
     set the step "blocked" with the reason in the progress file, stop THAT lane, keep
     independent lanes running, and surface a concise summary to me. Never stack a later step on
     a blocked prerequisite.

4) CONTEXT HYGIENE + ADVANCE:
   - Update docs/domain-specific-paddleboard-agent-progress.md (status, attempts, branch, merge
     SHA, one-line note incl. any CARRY-FORWARD; append one Log line).
   - Run /compact on YOURSELF (your durable state is the progress file, not the transcript).
   - Move to the next eligible step.

HARD GATES (never violate):
- Respect the dependency graph — start a step only when its prerequisites are "passed"; run
  independent steps (disjoint Edits files, no edge) in parallel; never let two steps that edit
  the same file overlap (S5→S6; S9→S10; S7→S12→S13; S16→S17).
- Never proceed past a step that isn't "passed"; never skip a Verify; never weaken a project
  rule or invariant to pass a check (grounding, refusal, contract freeze, legal disclaimer,
  offline determinism) — escalate to me instead.
- This greenfield build has NO destructive steps. The gates are S23–S26, each requiring my
  explicit written "go" recorded in the progress file Log BEFORE the step starts:
    S23 — HUMAN sign-off + PAID: live smoke with a real LLM_API_KEY (~cents). STOP before it;
          after it, a written GO/NO-GO must be in the Log before S24.
    S24 — PAID: live-model eval runs; one explicit "go" PER PROVIDER.
    S25 — HUMAN: manual demo-GIF screen capture; I perform the capture.
    S26 — HUMAN + EXTERNALLY VISIBLE: public GitHub publish; irreversible in spirit. STOP and
          require my explicit go; the pre-publish denylist grep and secret grep must both come
          back empty first.
- Never auto-run paid or live operations: no live LLM call and nothing that reads LLM_API_KEY
  anywhere in S1–S22; never `python evals/run_evals.py --mode live` (paid — S24 only, after go);
  never `gh repo create` or `git push` to any remote (externally visible — S26 only, after go).
  The unattended range ends at S22; surface that I must authorize each gate.
- Never edit any file outside this repo (the vault plan set stays untouched); inside the repo,
  the orchestration docs under docs/ are read-only except the progress file.

Begin now with SETUP, then S1. Report a one-line status after each step; keep prose minimal.
```

---

## Caveats (read before running)

1. **Greenfield bootstrap order matters.** The repo does not exist until S1 — you create the
   directory and copy the four docs into `docs/` BEFORE pasting (see How to use). S1 `git init`s
   in place and its first commit stages the four docs by name, so later per-step worktrees can
   read them. `docs/SPEC.md` is copied by S1 from the vault path hard-coded in S1's own prompt.
2. **Integration branch is `main`, not `<slug>/main`.** The generic template's `<slug>/main`
   collapses here: a fresh repo's trunk IS the integration branch (plan §0), and the steps'
   Verify blocks diff against `main` (e.g. S4's `git diff --stat main...HEAD -- app/schemas.py`).
   Nothing is public until S26, so `main` is safe as the merge target; the repo reaches GitHub
   only at the gated publish.
3. **No repo review agents exist.** Review routing is a fresh reviewer subagent per step with the
   inline checklist — that checklist (correctness, touched project rules, trust-boundary
   security, test adequacy, Verify authenticity) is the same one the workflow doc's Segment-1
   brief uses, so both runners hold the same bar. If you later install named review agents,
   remap in SETUP step 2.
4. **Fresh subagents are the real context-hygiene win** — each step's worker/reviewer starts
   clean and stays short-lived. The orchestrator's own `/compact` between steps, backed by the
   progress file as durable state, is the reliable part. Whether a spawned subagent can itself
   `/compact` depends on the CLI build; harmless if it can't.
5. **Fix worker = fresh by default.** Plain Task subagents are one-shot, so the fixer is a fresh
   worker given the branch diff + the review issues. If your environment supports resuming a
   prior agent with its context, the prompt may do that instead.
6. **Deferred live gates.** S23 (five live scenarios + /api/metrics spot-check), S24 (live eval
   tables), and S26's remote-CI-green + denylist/secret greps can't run in the offline loop —
   they are recorded in the progress file's "Deferred verification gate" section and run only at
   their gated steps, each after an explicit go.
7. **Cost shakeout first (plan R9).** 26 steps × (worker + reviewer + up to 3 fixers) adds up:
   run S1..S4 as a first slice, check subagent token spend, then continue with S5..S26. The
   progress file carries state across the two runs.
8. **Vault sync.** The run writes only the repo copy of the progress file. The vault copy at
   `Projects/github-portfolio/Plans/05-domain-specific-paddleboard-agent/` is the cross-session
   source of truth for the portfolio — mirror the repo copy back to the vault whenever the run
   pauses or finishes.
