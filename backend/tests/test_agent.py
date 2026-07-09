"""Tests for the S11 constrained agent (app.agent.agent): a fake chat model
replays canned tool-call transcripts, offline, against a tmp-path seeded
SQLite DB (same tmp-DB pattern as `test_tools_lookup.py`) — proving (a) a
requested tool call really executes and is logged as a `schemas.ToolCall`,
and (b)/(b2) the tool-iteration loop hard-stops at `MAX_TOOL_ITERATIONS`
(default 6, and independently at a small env-configured value) instead of
hanging on a model that requests tool calls forever. Rule (c): no test in
this module sets any `LLM_*` env var — the autouse fixture below actively
strips them so the module is offline regardless of the ambient shell.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage

from app.agent.agent import run_agent
from app.agent.tools import get_board
from app.db.seed import BOARDS_PATH, seed
from app.db.session import session_scope
from app.schemas import ToolCall


@pytest.fixture(autouse=True)
def _no_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)


def _tmp_db_url(tmp_path: Path, name: str = "test.sqlite3") -> str:
    return f"sqlite:///{tmp_path / name}"


def _seeded_db_url(tmp_path: Path) -> str:
    db_url = _tmp_db_url(tmp_path)
    with session_scope(db_url) as session:
        seed(session)
    return db_url


def _first_seeded_board_id() -> str:
    boards_data = json.loads(BOARDS_PATH.read_text())
    return str(boards_data["boards"][0]["id"])


class _FakeBoundModel:
    """Stand-in for `chat_model.bind_tools(tools)` — replays a fixed list of
    `AIMessage` responses, one per `.invoke()` call, ignoring the actual
    `tools`/`messages` passed in (the fakes below don't need real tool
    schemas to exercise the dispatch loop).
    """

    def __init__(self, responses: list[AIMessage]) -> None:
        self._responses = responses
        self.invoke_count = 0

    def invoke(self, _messages: list[Any]) -> AIMessage:
        response = self._responses[min(self.invoke_count, len(self._responses) - 1)]
        self.invoke_count += 1
        return response


class FakeChatModel:
    """Stand-in for `ChatOpenAI`: exposes only `.bind_tools(tools)`, exactly
    the surface `run_agent` relies on (decision §4.9 — duck-typed model
    injection, no real LangChain model or network call needed).
    """

    def __init__(self, responses: list[AIMessage]) -> None:
        self._responses = responses
        self.bound: _FakeBoundModel | None = None

    def bind_tools(self, _tools: list[Any]) -> _FakeBoundModel:
        self.bound = _FakeBoundModel(self._responses)
        return self.bound


class _ForeverToolCallModel:
    """A model that always requests a tool call, targeting an unknown tool
    name — never resolves to a real tool, so this exercises the iteration
    cap with zero DB/network dependency.
    """

    def __init__(self) -> None:
        self.invoke_count = 0

    def invoke(self, _messages: list[Any]) -> AIMessage:
        self.invoke_count += 1
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "not_a_real_tool",
                    "args": {},
                    "id": f"call_{self.invoke_count}",
                }
            ],
        )


class _ForeverChatModel:
    def __init__(self) -> None:
        self.bound: _ForeverToolCallModel | None = None

    def bind_tools(self, _tools: list[Any]) -> _ForeverToolCallModel:
        self.bound = _ForeverToolCallModel()
        return self.bound


# --- (a) a transcript calling get_board then answering ---------------------


def test_get_board_tool_call_executes_against_seeded_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_url = _seeded_db_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", db_url)
    board_id = _first_seeded_board_id()
    expected = get_board(board_id, database_url=db_url)
    assert expected is not None

    model = FakeChatModel(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_board",
                        "args": {"board_id": board_id},
                        "id": "call_1",
                    }
                ],
            ),
            AIMessage(content="Here is the board you asked about.", tool_calls=[]),
        ]
    )

    result = run_agent("Tell me about this board.", history=[], model=model)

    assert result["answer_text"] == "Here is the board you asked about."
    assert len(result["tool_calls"]) == 1
    tool_call = result["tool_calls"][0]
    assert isinstance(tool_call, ToolCall)
    assert tool_call.name == "get_board"
    assert tool_call.args == {"board_id": board_id}
    assert tool_call.latency_ms >= 0
    assert result["tool_results"][0]["id"] == expected.id
    assert result["tool_results"][0]["brand"] == expected.brand
    assert model.bound is not None
    assert model.bound.invoke_count == 2


# --- (b) a transcript that requests tool calls forever ---------------------


def test_forever_tool_calls_stop_at_default_cap() -> None:
    model = _ForeverChatModel()

    result = run_agent("Loop forever please.", history=[], model=model)

    assert model.bound is not None
    assert model.bound.invoke_count == 6
    assert len(result["tool_calls"]) == 6
    assert all(call.name == "not_a_real_tool" for call in result["tool_calls"])
    assert all(
        isinstance(res, dict) and "error" in res for res in result["tool_results"]
    )


def test_forever_tool_calls_stop_at_env_configured_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_TOOL_ITERATIONS", "2")
    model = _ForeverChatModel()

    result = run_agent("Loop forever please.", history=[], model=model)

    assert model.bound is not None
    assert model.bound.invoke_count == 2
    assert len(result["tool_calls"]) == 2


# --- adversarial tool-call args: exercise the except-path, not just the
# unknown-tool-name guard --------------------------------------------------


def test_malformed_tool_args_produce_error_result_and_loop_continues() -> None:
    model = FakeChatModel(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        # a real tool name, but args that fail pydantic
                        # validation (board_id is required, not supplied) —
                        # this is untrusted, model-supplied input.
                        "name": "get_board",
                        "args": {},
                        "id": "call_1",
                    }
                ],
            ),
            AIMessage(content="Sorry, I couldn't look that up.", tool_calls=[]),
        ]
    )

    result = run_agent("Look up a board with no id.", history=[], model=model)

    assert result["answer_text"] == "Sorry, I couldn't look that up."
    assert len(result["tool_calls"]) == 1
    assert isinstance(result["tool_results"][0], dict)
    assert "error" in result["tool_results"][0]
    assert model.bound is not None
    assert model.bound.invoke_count == 2
