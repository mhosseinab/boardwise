"""The `/api/chat` pipeline (S12): backstop -> agent -> grounding validator ->
assembled `ChatResponse` (SPEC "Backend requirements" items 3-5, plan §"the
project's integrity story").

Trust-boundary control flow (this module is reviewed by `bw-security-reviewer`,
not a standard step reviewer):

- **Refusal-before-agent ordering is enforced by control flow, not
  convention.** `handle_chat` checks `guardrails.is_in_domain` first and
  `return`s immediately when it is `False` — `run_agent` is never called, never
  referenced, and no model method is ever invoked on that code path. There is
  no shared branch, flag, or later gate that a caller could skip; the only way
  to reach `run_agent` in this function is to have already passed the domain
  check. This is the literal SPEC item 4 / project rule: "refusal = zero tool
  runs".
- **Ungrounded model output never reaches the response.** The agent's raw
  `answer_text` is never returned directly; it is always passed through
  `guardrails.validate_grounding` first, and only `GroundingResult.clean_answer`
  is used to build `ChatResponse.answer`.
- **The model's text is prose only.** `cards`, `tables`, and `compatibility`
  are built exclusively from that turn's typed tool results (`tool_calls` /
  `tool_results` returned by `run_agent`), never by parsing the model's answer
  text — the model cannot inject structured payloads by emitting markup or
  JSON in its prose.
"""

from typing import Any

from pydantic import ValidationError

from app.agent.agent import run_agent
from app.agent.guardrails import build_refusal, is_in_domain, validate_grounding
from app.prompts.loader import load_prompt
from app.schemas import (
    BoardCard,
    ChatRequest,
    ChatResponse,
    CompatibilityResult,
    SpecTable,
    ToolCall,
)

_SYSTEM_PROMPT_NAME = "system_v1"


def _try_board_card(value: Any) -> BoardCard | None:
    """Best-effort parse of a tool-result value as a `BoardCard`.

    Tool results are untrusted-shaped (a `get_board` miss is `None`, a failed
    tool call is `{"error": ...}`) — this never raises on a non-board value,
    it just yields no card.
    """
    if not isinstance(value, dict):
        return None
    try:
        return BoardCard.model_validate(value)
    except ValidationError:
        return None


def _try_compatibility_result(value: Any) -> CompatibilityResult | None:
    """Best-effort parse of a tool-result value as a `CompatibilityResult`."""
    if not isinstance(value, dict):
        return None
    try:
        return CompatibilityResult.model_validate(value)
    except ValidationError:
        return None


def _collect_cards_and_compatibility(
    tool_calls: list[ToolCall], tool_results: list[Any]
) -> tuple[list[BoardCard], list[CompatibilityResult]]:
    """Assemble `BoardCard`s and `CompatibilityResult`s server-side from that
    turn's tool results (rule: the server assembles structured payloads from
    tool results; the model never emits markup).

    `get_board` / `search_boards` / `recommend_setup` rows contribute cards,
    deduplicated by id in first-seen order. `check_compatibility` results and
    a `recommend_setup` bundle's own `compatibility` verdicts are passed
    through unchanged (SPEC item 5: "`CompatibilityResult` entries passed
    through").

    `tool_calls` and `tool_results` are positionally aligned — `run_agent`
    appends to both lists in lockstep, once per executed tool call.
    """
    cards_by_id: dict[str, BoardCard] = {}
    compatibility: list[CompatibilityResult] = []

    for call, result in zip(tool_calls, tool_results):
        if call.name == "get_board":
            card = _try_board_card(result)
            if card is not None:
                cards_by_id.setdefault(card.id, card)
        elif call.name == "search_boards":
            if isinstance(result, list):
                for row in result:
                    card = _try_board_card(row)
                    if card is not None:
                        cards_by_id.setdefault(card.id, card)
        elif call.name == "check_compatibility":
            verdict = _try_compatibility_result(result)
            if verdict is not None:
                compatibility.append(verdict)
        elif call.name == "recommend_setup":
            if isinstance(result, dict):
                card = _try_board_card(result.get("board"))
                if card is not None:
                    cards_by_id.setdefault(card.id, card)
                bundle_compatibility = result.get("compatibility")
                if isinstance(bundle_compatibility, list):
                    for entry in bundle_compatibility:
                        verdict = _try_compatibility_result(entry)
                        if verdict is not None:
                            compatibility.append(verdict)

    return list(cards_by_id.values()), compatibility


def _build_comparison_table(cards: list[BoardCard]) -> SpecTable | None:
    """A `SpecTable` comparing every distinct board surfaced this turn, when
    two or more are present (S12 prompt: "a `SpecTable` when >=2 boards are
    compared"). Board identity — not inferred intent — drives the trigger:
    any turn that surfaces two or more distinct boards (two `get_board`
    lookups, a multi-row `search_boards` result, or a `recommend_setup`
    bundle alongside another lookup) gets a side-by-side comparison table.
    """
    if len(cards) < 2:
        return None
    columns = [
        "Board",
        "Length (ft)",
        "Width (in)",
        "Volume (L)",
        "Capacity (kg)",
        "Recommended PSI",
        "Price (USD)",
    ]
    rows = [
        [
            f"{card.brand} {card.model}",
            f"{card.length_ft:g}",
            f"{card.width_in:g}",
            f"{card.volume_l:g}",
            f"{card.max_rider_weight_kg:g}",
            str(card.recommended_psi),
            f"{card.price_usd:g}",
        ]
        for card in cards
    ]
    return SpecTable(
        title="Board comparison",
        columns=columns,
        rows=rows,
        board_ids=[card.id for card in cards],
    )


def handle_chat(request: ChatRequest, model: Any = None) -> ChatResponse:
    """Compose the S12 `/api/chat` pipeline for one turn.

    1. `guardrails.is_in_domain` — an out-of-domain message returns a refusal
       immediately, with zero tools run and `run_agent` never invoked.
    2. `run_agent` — the constrained tool-calling agent (S11).
    3. `guardrails.validate_grounding` — strips any spec/number in the
       answer absent from that turn's tool results (S9).
    4. Server-side assembly of `cards` / `tables` / `compatibility` from the
       tool results (never from the model's text).

    `model` is forwarded to `run_agent` unchanged (decision §4.9 — duck-typed
    model injection); tests inject a fake, offline model here exactly as
    `test_agent.py` does for `run_agent` directly.
    """
    _system_text, prompt_version = load_prompt(_SYSTEM_PROMPT_NAME)

    if not is_in_domain(request.message):
        return ChatResponse(
            answer=build_refusal(),
            refused=True,
            prompt_version=prompt_version,
        )

    agent_result = run_agent(request.message, request.history, model=model)
    tool_calls: list[ToolCall] = agent_result["tool_calls"]
    tool_results: list[Any] = agent_result["tool_results"]

    grounding = validate_grounding(agent_result["answer_text"], tool_results)
    cards, compatibility = _collect_cards_and_compatibility(tool_calls, tool_results)
    table = _build_comparison_table(cards)

    return ChatResponse(
        answer=grounding.clean_answer,
        cards=cards,
        tables=[table] if table is not None else [],
        compatibility=compatibility,
        tools_used=tool_calls,
        refused=False,
        prompt_version=prompt_version,
    )
