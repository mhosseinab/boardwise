---
name: gate-check
description: Runs the pre-gate confirmation procedure for BoardWise's S23 (paid live smoke) / S24 (paid live eval) / S25 (human demo GIF) / S26 (human, publish) boundaries — reads the progress file, verifies prerequisite steps are passed, and drafts the go/spend-ack Log line. User-invoked only; never auto-runs a gate.
disable-model-invocation: true
---

# Gate Check — BoardWise

Use before manually running S23, S24, S25, or S26. This skill only *checks and drafts* — it never
performs the gated action itself (no live LLM call, no `git push`, no `gh repo create`).

## Usage
`/gate-check S23` (or `S24` / `S25` / `S26`)

## Procedure

### S23 — HUMAN sign-off + PAID (live smoke with a real `LLM_API_KEY`)
1. Read `docs/domain-specific-paddleboard-agent-progress.md`. Confirm S1–S22 are all `passed`.
2. Confirm `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` are set in the environment.
3. Draft (do not commit) a Log line: go + spend acknowledgment (~cents) naming the model.
4. Report readiness. Only after the user gives an explicit written "go" recorded in the Log should
   S23 run, in a normal supervised session.

### S24 — PAID (live-model eval runs, one explicit "go" per provider)
1. Confirm S23 is `passed` with its GO/NO-GO recorded in the Log.
2. For each provider being evaluated, confirm a separate explicit "go" exists (or is being given
   now) — S24 requires per-provider authorization, not one blanket go.
3. Draft the Log line for the provider(s) about to run.
4. Never invoke `python evals/run_evals.py --mode live` yourself — report readiness only.

### S25 — HUMAN (manual demo-GIF screen capture; README finalization)
1. Confirm S24 is `passed`.
2. Surface the checklist the human should walk through at the keyboard: the mock-data disclaimer
   visible on screen, a representative grounded-answer example, a refusal example, and the
   live-eval numbers slotted into the README's placeholder table.
3. Draft the go/no-go Log line once the human has actually looked.

### S26 — HUMAN + EXTERNALLY VISIBLE (public GitHub publish)
1. Confirm S23, S24, S25 are all `passed`.
2. Run the pre-publish scans FIRST, before any repo creation or push:
   ```
   bash .claude/skills/gate-check/scripts/denylist_grep.sh
   bash .claude/skills/gate-check/scripts/secret_scan.sh
   ```
   Both must come back empty. Non-empty output is a hard blocker — report exact file:line matches;
   do not edit or strip data yourself.
3. Confirm the mock-data disclaimer is present in both `README.md` and the frontend UI banner.
4. Draft the written-go Log line and list the plan's §11 Definition-of-done checklist items that
   must be re-verified with fresh evidence during the S26 session (not assumed from earlier steps).

## Hard rule
This skill never itself runs `make eval` in live mode, calls a live LLM, pushes, or invokes `gh`.
It only confirms prerequisites, runs the (non-destructive, read-only) pre-publish scans, and drafts
the Log entry — the gated action is always a separate, explicit, human-launched step.
