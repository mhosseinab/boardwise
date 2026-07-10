"""Tests for the S12 `/api/chat` pipeline (`app.agent.pipeline.handle_chat`):
the two SPEC signature tests plus a grounded happy path. A fake chat model
replays canned tool-call transcripts, offline, against a tmp-path seeded
SQLite DB (same pattern as `test_agent.py`) — no test in this module sets
any `LLM_*` env var, and the autouse fixture below actively strips them so
the module is offline regardless of the ambient shell.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage

from app.agent.pipeline import handle_chat
from app.db.seed import BOARDS_PATH, seed
from app.db.session import session_scope
from app.schemas import ChatRequest, ChatResponse


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
    `AIMessage` responses, one per `.invoke()` call (same shape as
    `test_agent.py`'s fake).
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
    the surface `run_agent` relies on. Tracks whether it was ever invoked so
    SIGNATURE TEST B can assert the agent/model is never reached on a
    refused turn.
    """

    def __init__(self, responses: list[AIMessage]) -> None:
        self._responses = responses
        self.bound: _FakeBoundModel | None = None
        self.bind_tools_called = False

    def bind_tools(self, _tools: list[Any]) -> _FakeBoundModel:
        self.bind_tools_called = True
        self.bound = _FakeBoundModel(self._responses)
        return self.bound


class _AssertNeverInvokedModel:
    """A model that raises if it is ever touched — used to prove a refused
    turn never reaches `run_agent`/the model, not just that the eventual
    answer happens to be empty of tool calls.
    """

    def __init__(self) -> None:
        self.bind_tools_called = False

    def bind_tools(self, _tools: list[Any]) -> Any:
        self.bind_tools_called = True
        raise AssertionError("model must never be invoked on a refused turn")


# --- SIGNATURE TEST A: no-ungrounded-spec -----------------------------------


def test_signature_no_ungrounded_spec_is_stripped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The model asserts a PSI and a price absent from that turn's tool
    results; the grounding guardrail must strip both and the response must
    say "I don't have that spec" instead — the core anti-hallucination
    guarantee (SPEC "Testing" — "No-ungrounded-spec test").
    """
    db_url = _seeded_db_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", db_url)
    board_id = _first_seeded_board_id()

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
            AIMessage(
                content=(
                    "This board is rated to an eye-watering 999 psi and "
                    "costs $99999. It's a great pick for touring."
                ),
                tool_calls=[],
            ),
        ]
    )

    response = handle_chat(
        ChatRequest(message="Tell me about this paddleboard's specs."), model=model
    )

    assert isinstance(response, ChatResponse)
    assert response.refused is False
    assert "999 psi" not in response.answer
    assert "$99999" not in response.answer
    assert "99999" not in response.answer
    assert "I don't have that spec" in response.answer
    assert model.bound is not None
    assert model.bound.invoke_count == 2


# --- SIGNATURE TEST B: off-topic refusal ------------------------------------


def test_signature_off_topic_refusal_runs_zero_tools_and_never_invokes_model() -> None:
    """An out-of-domain message must be refused with zero tools run, and the
    agent/model must never be invoked at all — the refusal is enforced by
    control flow (an early `return` before `run_agent` is ever referenced),
    not merely by the eventual absence of tool calls (SPEC "Testing" —
    "Off-topic refusal test").
    """
    model = _AssertNeverInvokedModel()

    response = handle_chat(
        ChatRequest(message="write me a poem about the sea"), model=model
    )

    assert isinstance(response, ChatResponse)
    assert response.refused is True
    assert response.tools_used == []
    assert response.cards == []
    assert response.tables == []
    assert response.compatibility == []
    assert response.prompt_version
    assert model.bind_tools_called is False


# --- grounded happy path -----------------------------------------------------


def test_grounded_happy_path_returns_board_card(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_url = _seeded_db_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", db_url)
    board_id = _first_seeded_board_id()

    from app.agent.tools import get_board

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
            AIMessage(
                content=(
                    f"The {expected.brand} {expected.model} is priced at "
                    f"${expected.price_usd:g} and rated to "
                    f"{expected.recommended_psi} psi."
                ),
                tool_calls=[],
            ),
        ]
    )

    response = handle_chat(
        ChatRequest(message="Tell me about this paddleboard's price and psi."),
        model=model,
    )

    assert response.refused is False
    assert len(response.cards) >= 1
    assert response.cards[0].id == board_id
    assert f"${expected.price_usd:g}" in response.answer
    assert response == ChatResponse.model_validate(response.model_dump())
