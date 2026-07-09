# Prompts and the guardrail story

Prompts live here as versioned files, not inline strings in application code — no other
module may embed prompt text. `loader.py` reads a prompt by name (e.g. `"system_v1"`) and
returns `(text, prompt_version)`; every `ChatResponse` stamps the `prompt_version` that produced
it.

- `system_v1.md` — the domain-constraint system prompt: scopes the agent to SUP gear, requires
  every spec/number to trace to a tool result, instructs refusal for off-topic requests, and
  forbids markup in answers.
- `tools_v1.md` — descriptions of the four catalog tools (`get_board`, `search_boards`,
  `check_compatibility`, `recommend_setup`), matching the signatures implemented in
  `backend/app/agent/tools.py`.

Rule: keep this README truthful — update it in the same commit as any prompt change.

## The three guardrail layers

BoardWise's anti-hallucination and off-topic protection is not "ask the model nicely." It is
three independent layers, only the first of which is a prompt:

1. **System prompt (this step, S8).** `system_v1.md` instructs the model to ground every
   spec/number in tool results and to refuse anything off-topic. This is the first line of
   defense, but a prompt alone is not enforcement — a model can still ignore it.
2. **Code-level grounding validator (`backend/app/agent/guardrails.py`, built at S9).**
   `validate_grounding` is a pure function that inspects the agent's answer against the union of
   that turn's tool results and strips or replaces any spec/number that cannot be traced back to
   a tool result, regardless of what the model said. This is where the grounding invariant is
   actually enforced — in code, not in the prompt.
3. **Refusal backstop (`backend/app/agent/guardrails.py`, built at S10).** `is_in_domain` is a
   deterministic heuristic classifier (no model call) that runs before the agent is invoked. If
   a message looks off-topic — including jailbreak-shaped attempts to override the system
   prompt — the pipeline short-circuits to a refusal with zero tool runs, independent of what the
   system prompt would have produced.

Only layer 1 exists as of this step. Layers 2 and 3 are built in S9 and S10 and composed into
the `/api/chat` pipeline at S12; this document is updated as each lands.
