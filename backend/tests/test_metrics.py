"""Tests for S13 observability: one structured JSON log line per `/api/chat`
request and the in-process `GET /api/metrics` registry (SPEC "Backend
requirements" item 6).

`app.main.chat()` is exercised end-to-end via FastAPI's `TestClient`, with
`app.main.handle_chat` monkeypatched to canned `ChatResponse`s (one refused,
one grounded) so this stays fully offline — the S12 pipeline itself is
frozen for this step and out of scope; only what `main.py`'s route can
observe around it (latency, `tools_used`, `refused`, `prompt_version`) is
under test here.
"""

import json
import logging
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.observability import metrics_registry
from app.schemas import ChatResponse, ToolCall


@pytest.fixture(autouse=True)
def _reset_metrics_registry() -> Iterator[None]:
    """The metrics registry is a process-global singleton — reset it before
    and after every test so tests never leak counts into each other."""
    metrics_registry.reset()
    yield
    metrics_registry.reset()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(main_module.app)


def _refused_response() -> ChatResponse:
    return ChatResponse(
        answer="I only cover paddleboards and gear — happy to help with that!",
        refused=True,
        prompt_version="system_v1",
    )


def _grounded_response() -> ChatResponse:
    return ChatResponse(
        answer="The Aquara Atlas 12'0\" is a solid touring pick.",
        tools_used=[
            ToolCall(
                name="get_board",
                args={"board_id": "aquara-atlas-12"},
                result_summary='{"id": "aquara-atlas-12"}',
                latency_ms=4,
            ),
            ToolCall(
                name="search_boards",
                args={"board_type": "touring"},
                result_summary="[...]",
                latency_ms=6,
            ),
        ],
        refused=False,
        prompt_version="system_v1",
    )


def test_metrics_after_two_chat_calls_reports_expected_aggregates(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One refused turn (0 tools) + one grounded turn (2 tools) ->
    requests=2, refusal_rate=0.5, avg_tools_per_turn=1.0, matching the
    canned transcripts exactly."""
    responses = iter([_refused_response(), _grounded_response()])
    monkeypatch.setattr(main_module, "handle_chat", lambda request: next(responses))

    first = client.post("/api/chat", json={"message": "write me a poem"})
    second = client.post("/api/chat", json={"message": "tell me about a board"})

    assert first.status_code == 200
    assert second.status_code == 200

    metrics_response = client.get("/api/metrics")
    assert metrics_response.status_code == 200
    body = metrics_response.json()

    assert body["requests"] == 2
    assert body["refusal_rate"] == pytest.approx(0.5)
    assert body["avg_tools_per_turn"] == pytest.approx(1.0)
    assert body["p50_ms"] >= 0
    assert body["p95_ms"] >= 0


def test_metrics_with_zero_requests_reports_zeroed_aggregates(
    client: TestClient,
) -> None:
    body = client.get("/api/metrics").json()
    assert body == {
        "requests": 0,
        "p50_ms": 0.0,
        "p95_ms": 0.0,
        "refusal_rate": 0.0,
        "avg_tools_per_turn": 0.0,
    }


def test_chat_request_emits_one_json_log_line_with_required_keys(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        main_module, "handle_chat", lambda request: _grounded_response()
    )

    with caplog.at_level(logging.INFO, logger="boardwise.observability"):
        response = client.post("/api/chat", json={"message": "tell me about a board"})
    assert response.status_code == 200

    log_records = [
        record for record in caplog.records if record.name == "boardwise.observability"
    ]
    assert len(log_records) == 1

    payload = json.loads(log_records[0].getMessage())
    for key in (
        "request_id",
        "latency_ms",
        "tools",
        "token_counts",
        "estimated_cost_usd",
        "refused",
        "prompt_version",
    ):
        assert key in payload

    assert payload["tools"] == ["get_board", "search_boards"]
    assert payload["refused"] is False
    assert payload["prompt_version"] == "system_v1"
    assert payload["token_counts"] is None
    assert payload["estimated_cost_usd"] is None
    assert isinstance(payload["latency_ms"], int)
    assert payload["request_id"]
