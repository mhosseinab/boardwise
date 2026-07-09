"""Tests for the S5 lookup tools (app.agent.tools): `get_board` and
`search_boards`, run against a tmp-path seeded SQLite DB (same fixture
pattern as `test_seed.py`).
"""

import json
from pathlib import Path

from app.agent.tools import get_board, search_boards
from app.db.seed import BOARDS_PATH, seed
from app.db.session import session_scope


def _tmp_db_url(tmp_path: Path, name: str = "test.sqlite3") -> str:
    return f"sqlite:///{tmp_path / name}"


def _seeded_db_url(tmp_path: Path) -> str:
    db_url = _tmp_db_url(tmp_path)
    with session_scope(db_url) as session:
        seed(session)
    return db_url


def _board_ids(cards: list) -> list[str]:
    return [card.id for card in cards]


# --- get_board -----------------------------------------------------------


def test_get_board_returns_exact_seeded_row(tmp_path: Path) -> None:
    db_url = _seeded_db_url(tmp_path)
    boards_data = json.loads(BOARDS_PATH.read_text())
    sample = boards_data["boards"][0]

    card = get_board(sample["id"], database_url=db_url)

    assert card is not None
    assert card.id == sample["id"]
    assert card.brand == sample["brand"]
    assert card.model == sample["model"]
    assert card.length_ft == sample["length_ft"]
    assert card.width_in == sample["width_in"]
    assert card.thickness_in == sample["thickness_in"]
    assert card.volume_l == sample["volume_l"]
    assert card.max_rider_weight_kg == sample["max_rider_weight_kg"]
    assert card.recommended_psi == sample["recommended_psi"]
    assert card.max_psi == sample["max_psi"]
    assert card.board_type == sample["board_type"]
    assert card.skill_level == sample["skill_level"]
    assert card.fin_box == sample["fin_box"]
    assert card.valve_type == sample["valve_type"]
    assert card.board_weight_kg == sample["board_weight_kg"]
    assert card.price_usd == sample["price_usd"]
    assert card.best_for == sample["best_for"]
    assert card.image_url == sample["image_url"]
    assert card.is_mock == sample["is_mock"]


def test_get_board_unknown_id_returns_none(tmp_path: Path) -> None:
    db_url = _seeded_db_url(tmp_path)

    assert get_board("brd-does-not-exist", database_url=db_url) is None


# --- search_boards: single filters ----------------------------------------


def test_search_boards_no_filters_returns_all_seeded_boards(tmp_path: Path) -> None:
    db_url = _seeded_db_url(tmp_path)
    boards_data = json.loads(BOARDS_PATH.read_text())

    cards = search_boards({}, database_url=db_url)

    assert _board_ids(cards) == sorted(b["id"] for b in boards_data["boards"])


def test_search_boards_filters_by_board_type(tmp_path: Path) -> None:
    db_url = _seeded_db_url(tmp_path)

    cards = search_boards({"board_type": "yoga"}, database_url=db_url)

    assert _board_ids(cards) == ["brd-004", "brd-005", "brd-006"]
    assert all(card.board_type == "yoga" for card in cards)


def test_search_boards_filters_by_skill_level(tmp_path: Path) -> None:
    db_url = _seeded_db_url(tmp_path)

    cards = search_boards({"skill_level": "beginner"}, database_url=db_url)

    assert _board_ids(cards) == [
        "brd-001",
        "brd-004",
        "brd-007",
        "brd-010",
        "brd-013",
    ]
    assert all(card.skill_level == "beginner" for card in cards)


def test_search_boards_min_capacity_kg_is_greater_or_equal(tmp_path: Path) -> None:
    db_url = _seeded_db_url(tmp_path)

    cards = search_boards({"min_capacity_kg": 115}, database_url=db_url)

    # brd-003, brd-011, brd-015 sit exactly at 115 kg capacity and must be
    # included: `>=`, not `>`.
    assert _board_ids(cards) == [
        "brd-001",
        "brd-002",
        "brd-003",
        "brd-004",
        "brd-005",
        "brd-011",
        "brd-013",
        "brd-014",
        "brd-015",
    ]
    assert all(card.max_rider_weight_kg >= 115 for card in cards)


def test_search_boards_filters_by_price_range(tmp_path: Path) -> None:
    db_url = _seeded_db_url(tmp_path)

    cards = search_boards(
        {"min_price_usd": 700, "max_price_usd": 800}, database_url=db_url
    )

    assert _board_ids(cards) == ["brd-002", "brd-006", "brd-009", "brd-010", "brd-015"]
    assert all(700 <= card.price_usd <= 800 for card in cards)


def test_search_boards_filters_by_length_range(tmp_path: Path) -> None:
    db_url = _seeded_db_url(tmp_path)

    cards = search_boards(
        {"min_length_ft": 12, "max_length_ft": 13}, database_url=db_url
    )

    assert _board_ids(cards) == ["brd-002", "brd-003", "brd-010"]
    assert all(12 <= card.length_ft <= 13 for card in cards)


# --- search_boards: combined filters ---------------------------------------


def test_search_boards_combined_type_and_skill_filters(tmp_path: Path) -> None:
    db_url = _seeded_db_url(tmp_path)

    cards = search_boards(
        {"board_type": "touring", "skill_level": "intermediate"},
        database_url=db_url,
    )

    assert _board_ids(cards) == ["brd-002"]


def test_search_boards_combined_type_and_capacity_filters(tmp_path: Path) -> None:
    db_url = _seeded_db_url(tmp_path)

    cards = search_boards(
        {"board_type": "all-around", "min_capacity_kg": 120}, database_url=db_url
    )

    assert _board_ids(cards) == ["brd-013", "brd-014"]


def test_search_boards_no_match_returns_empty_list(tmp_path: Path) -> None:
    db_url = _seeded_db_url(tmp_path)

    cards = search_boards(
        {"board_type": "yoga", "skill_level": "advanced", "min_price_usd": 10000},
        database_url=db_url,
    )

    assert cards == []
