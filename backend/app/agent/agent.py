"""The constrained BoardWise agent (SPEC "Backend requirements" item 2 — the
headline engineering feature): a LangChain tool-calling loop wired to the
four S5/S6 tools, the versioned S8 prompts, a hard cap on tool iterations,
and per-call `ToolCall` logging.

Model injection (decision §4.9): `run_agent`'s `model` parameter accepts any
object exposing the same duck-typed `bind_tools(tools).invoke(messages)`
interface `langchain_openai.ChatOpenAI` implements — tests inject a fake
replaying canned transcripts, offline, so no network call or `LLM_API_KEY`
is ever required to exercise this module. `build_default_model` is the only
place a real model is constructed, and only from
`LLM_BASE_URL`/`LLM_API_KEY`/`LLM_MODEL` env (rule: no hardcoded provider or
key); it is never called by this module's own tests.

Scope (rule, S11 prompt): no grounding/refusal composition here — S12 wires
`guardrails.py` and the refusal backstop around this function's output. No
route changes.

Trust boundary note: tool-call `name`/`args` in `ai_message.tool_calls`
originate from the model's response and must be treated as untrusted input.
Dispatch here never `eval`s/`exec`s anything; args are validated by each
`StructuredTool`'s pydantic `args_schema` before the wrapped S5/S6 function
ever runs, and those functions only ever reach the DB through SQLAlchemy's
parameterized query builder (see `app/agent/tools.py`) — never raw SQL
string interpolation. An unknown tool name or a tool call that fails
validation/execution is recorded as an error result, not raised, so a
malformed or adversarial tool-call request can't crash the turn.
"""

import json
import os
import re
import time
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr

from app.agent.tools import (
    BoardSearchFilters,
    RiderProfile,
    check_compatibility,
    get_board,
    recommend_setup,
    search_boards,
)
from app.prompts.loader import load_prompt
from app.schemas import ToolCall

DEFAULT_MAX_TOOL_ITERATIONS = 6

_SYSTEM_PROMPT_NAME = "system_v1"
_TOOLS_PROMPT_NAME = "tools_v1"
_SECTION_HEADING = re.compile(r"^## (.+)$", re.MULTILINE)


# --- tool argument schemas ---------------------------------------------


class GetBoardArgs(BaseModel):
    board_id: str = Field(description="Catalog id of the board to look up.")


class SearchBoardsArgs(BaseModel):
    board_type: str | None = None
    skill_level: str | None = None
    min_capacity_kg: float | None = None
    min_price_usd: float | None = None
    max_price_usd: float | None = None
    min_length_ft: float | None = None
    max_length_ft: float | None = None


class CheckCompatibilityArgs(BaseModel):
    board_id: str
    accessory_id: str


class RecommendSetupArgs(BaseModel):
    weight_kg: float
    height_cm: float
    skill_level: str
    use_case: str
    budget_usd: float | None = None


def _to_jsonable(value: Any) -> Any:
    """Recursively convert `schemas`/`TypedDict` tool results into plain
    JSON-serializable data (for the `ToolMessage` content and result_summary).
    """
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    return value


# --- tool wrappers (public args only — `database_url` stays internal DI) --


def _get_board_tool(board_id: str) -> Any:
    return _to_jsonable(get_board(board_id))


def _search_boards_tool(
    board_type: str | None = None,
    skill_level: str | None = None,
    min_capacity_kg: float | None = None,
    min_price_usd: float | None = None,
    max_price_usd: float | None = None,
    min_length_ft: float | None = None,
    max_length_ft: float | None = None,
) -> Any:
    filters: BoardSearchFilters = {}
    if board_type is not None:
        filters["board_type"] = board_type
    if skill_level is not None:
        filters["skill_level"] = skill_level
    if min_capacity_kg is not None:
        filters["min_capacity_kg"] = min_capacity_kg
    if min_price_usd is not None:
        filters["min_price_usd"] = min_price_usd
    if max_price_usd is not None:
        filters["max_price_usd"] = max_price_usd
    if min_length_ft is not None:
        filters["min_length_ft"] = min_length_ft
    if max_length_ft is not None:
        filters["max_length_ft"] = max_length_ft
    return _to_jsonable(search_boards(filters))


def _check_compatibility_tool(board_id: str, accessory_id: str) -> Any:
    return _to_jsonable(check_compatibility(board_id, accessory_id))


def _recommend_setup_tool(
    weight_kg: float,
    height_cm: float,
    skill_level: str,
    use_case: str,
    budget_usd: float | None = None,
) -> Any:
    rider_profile: RiderProfile = {
        "weight_kg": weight_kg,
        "height_cm": height_cm,
        "skill_level": skill_level,
        "use_case": use_case,
    }
    if budget_usd is not None:
        rider_profile["budget_usd"] = budget_usd
    return _to_jsonable(recommend_setup(rider_profile))


def _load_tool_descriptions() -> dict[str, str]:
    """Parse `tools_v1.md`'s `## <tool_name>` sections into a name->
    description map, so tool descriptions live only in the prompt asset
    (rule: prompts are assets, never inline strings).
    """
    text, _prompt_version = load_prompt(_TOOLS_PROMPT_NAME)
    headings = list(_SECTION_HEADING.finditer(text))
    descriptions: dict[str, str] = {}
    for index, match in enumerate(headings):
        name = match.group(1).strip()
        start = match.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        descriptions[name] = text[start:end].strip()
    return descriptions


def build_tools() -> list[StructuredTool]:
    """Wrap the four S5/S6 tool functions as LangChain `StructuredTool`s,
    with descriptions sourced from `tools_v1.md`.
    """
    descriptions = _load_tool_descriptions()
    return [
        StructuredTool.from_function(
            func=_get_board_tool,
            name="get_board",
            description=descriptions["get_board"],
            args_schema=GetBoardArgs,
        ),
        StructuredTool.from_function(
            func=_search_boards_tool,
            name="search_boards",
            description=descriptions["search_boards"],
            args_schema=SearchBoardsArgs,
        ),
        StructuredTool.from_function(
            func=_check_compatibility_tool,
            name="check_compatibility",
            description=descriptions["check_compatibility"],
            args_schema=CheckCompatibilityArgs,
        ),
        StructuredTool.from_function(
            func=_recommend_setup_tool,
            name="recommend_setup",
            description=descriptions["recommend_setup"],
            args_schema=RecommendSetupArgs,
        ),
    ]


def build_default_model() -> ChatOpenAI:
    """Build the OpenAI-compatible chat model from env (rule: no hardcoded
    provider/key). Never called by this module's own tests — only reachable
    when `run_agent` is invoked without an injected `model`.
    """
    raw_api_key = os.environ.get("LLM_API_KEY")
    return ChatOpenAI(
        base_url=os.environ.get("LLM_BASE_URL"),
        api_key=SecretStr(raw_api_key) if raw_api_key is not None else None,
        model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
        temperature=0,
    )


def _history_to_messages(history: list[Any] | None) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    for turn in history or []:
        role = turn.get("role")
        content = turn.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    return messages


def _summarize(result: Any) -> str:
    text = json.dumps(result, default=str)
    if len(text) <= 200:
        return text
    return text[:197] + "..."


def _max_tool_iterations() -> int:
    raw = os.environ.get("MAX_TOOL_ITERATIONS")
    if raw is None:
        return DEFAULT_MAX_TOOL_ITERATIONS
    return int(raw)


def run_agent(
    message: str, history: list[Any] | None, model: Any = None
) -> dict[str, Any]:
    """Run the constrained tool-calling agent for one turn.

    Each iteration is one model call: if it requests tool calls, every
    requested call is executed and recorded before the next iteration; the
    loop stops as soon as a model response requests no further tool calls,
    or after `MAX_TOOL_ITERATIONS` (env, default 6) iterations, whichever
    comes first — so a model that requests tool calls forever cannot hang or
    exceed the cap. No grounding/refusal composition here (S12 composes
    them from this function's output).
    """
    chat_model = model if model is not None else build_default_model()
    tools = build_tools()
    tools_by_name = {tool.name: tool for tool in tools}
    model_with_tools = chat_model.bind_tools(tools)

    system_text, _prompt_version = load_prompt(_SYSTEM_PROMPT_NAME)
    messages: list[BaseMessage] = [SystemMessage(content=system_text)]
    messages.extend(_history_to_messages(history))
    messages.append(HumanMessage(content=message))

    tool_calls: list[ToolCall] = []
    tool_results: list[Any] = []
    ai_message: BaseMessage | None = None

    for _iteration in range(_max_tool_iterations()):
        ai_message = model_with_tools.invoke(messages)
        messages.append(ai_message)
        requested = list(getattr(ai_message, "tool_calls", None) or [])
        if not requested:
            break
        for call in requested:
            name = call["name"]
            args = dict(call.get("args") or {})
            call_id = call.get("id") or name
            tool = tools_by_name.get(name)
            started = time.perf_counter()
            result: Any
            try:
                if tool is None:
                    result = {"error": f"unknown tool: {name}"}
                else:
                    result = tool.invoke(args)
            except Exception as exc:  # untrusted model-supplied args/name
                result = {"error": f"tool call failed: {exc}"}
            latency_ms = int((time.perf_counter() - started) * 1000)
            tool_calls.append(
                ToolCall(
                    name=name,
                    args=args,
                    result_summary=_summarize(result),
                    latency_ms=latency_ms,
                )
            )
            tool_results.append(result)
            messages.append(
                ToolMessage(
                    content=json.dumps(result, default=str), tool_call_id=call_id
                )
            )

    answer_text = ""
    if ai_message is not None:
        content = ai_message.content
        answer_text = content if isinstance(content, str) else str(content)

    return {
        "answer_text": answer_text,
        "tool_calls": tool_calls,
        "tool_results": tool_results,
    }
