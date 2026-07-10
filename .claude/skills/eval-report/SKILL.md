---
name: eval-report
description: Run BoardWise's eval harness and summarize correctness/grounding/refusal results, distinguishing offline (mocked) from live-model runs.
disable-model-invocation: true
---

# Eval report

BoardWise's eval harness (`make eval`, added at S19) is the project's central proof artifact: it
measures — not asserts — correctness, grounding, and refusal rate. Offline runs use the mocked LLM
and are safe in default CI; live-model runs (`evals/run_evals.py --mode live`) are paid and gated
to S24, one explicit "go" per provider (plan §10 R2, R5).

## Steps

1. Confirm mode before running anything:
   - Default to **offline**: `make eval` (or `python evals/run_evals.py --mode offline` if `make`
     isn't set up yet).
   - Only run **live** mode if the user has explicitly authorized it for this session — this reads
     `LLM_API_KEY` and costs money. Never run it unprompted, and never run it as part of default CI
     or S1–S22 work.

2. Run the chosen command and capture full output.

3. Parse the correctness / grounding / refusal table from the output and present it plainly:
   | Metric | Offline | Live (model X) |
   |---|---|---|
   | Correctness | | |
   | Grounding | | |
   | Refusal rate | | |

   If a live run wasn't performed this session, leave that column blank rather than inventing
   numbers — this table is what README.md quotes at S22/S25, so it must reflect only fresh,
   actually-executed runs.

4. Flag any regression versus the last recorded numbers in `docs/domain-specific-paddleboard-agent-progress.md`
   (if that file has prior eval numbers logged), and note it — don't silently overwrite history.
