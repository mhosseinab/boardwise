"""Tests for the S7 catalog API (app.main): `/api/health`, `/api/boards`,
`/api/boards/{id}`, run against a tmp-path seeded SQLite DB (same
tmp-DB pattern as `test_seed.py`/`test_tools_lookup.py`, wired in via the
`DATABASE_URL` env var since `app.main`'s handlers call the S5 tools with
no explicit `database_url`).
"""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.seed import BOARDS_PATH
from app.main import app
from app.schemas import BoardCard


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    db_url = f"sqlite:///{tmp_path / 'test_api.sqlite3'}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    with TestClient(app) as test_client:
        yield test_client


def _seeded_board_count() -> int:
    boards_data = json.loads(BOARDS_PATH.read_text())
    return len(boards_data["boards"])


def _seeded_beginner_count() -> int:
    boards_data = json.loads(BOARDS_PATH.read_text())
    return sum(1 for b in boards_data["boards"] if b["skill_level"] == "beginner")


# --- /api/health -------------------------------------------------------


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --- /api/boards ---------------------------------------------------------


def test_unfiltered_boards_returns_seeded_count(client: TestClient) -> None:
    response = client.get("/api/boards")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == _seeded_board_count()
    for row in body:
        BoardCard.model_validate(row)


def test_skill_level_beginner_returns_only_beginner_boards(
    client: TestClient,
) -> None:
    response = client.get("/api/boards", params={"skill_level": "beginner"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == _seeded_beginner_count()
    assert all(row["skill_level"] == "beginner" for row in body)


def test_pagination_window_is_correct(client: TestClient) -> None:
    full = client.get("/api/boards").json()

    page = client.get("/api/boards", params={"limit": 2, "offset": 1}).json()

    assert [row["id"] for row in page] == [row["id"] for row in full[1:3]]


def test_min_capacity_kg_filter_maps_to_search_boards(client: TestClient) -> None:
    response = client.get("/api/boards", params={"min_capacity_kg": 115})

    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    assert all(row["max_rider_weight_kg"] >= 115 for row in body)


def test_max_price_usd_filter_maps_to_search_boards(client: TestClient) -> None:
    response = client.get("/api/boards", params={"max_price_usd": 800})

    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    assert all(row["price_usd"] <= 800 for row in body)


def test_length_range_filter_maps_to_search_boards(client: TestClient) -> None:
    response = client.get(
        "/api/boards", params={"min_length_ft": 12, "max_length_ft": 13}
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    assert all(12 <= row["length_ft"] <= 13 for row in body)


# --- /api/boards/{id} ------------------------------------------------------


def test_get_board_by_id_returns_seeded_board(client: TestClient) -> None:
    boards_data = json.loads(BOARDS_PATH.read_text())
    sample = boards_data["boards"][0]

    response = client.get(f"/api/boards/{sample['id']}")

    assert response.status_code == 200
    card = BoardCard.model_validate(response.json())
    assert card.id == sample["id"]
    assert card.brand == sample["brand"]


def test_get_board_by_unknown_id_returns_404(client: TestClient) -> None:
    response = client.get("/api/boards/brd-does-not-exist")

    assert response.status_code == 404
