"""Tests for the idempotent seeder (app.db.seed) against a tmp_path SQLite DB."""

import json
from pathlib import Path

from sqlalchemy import select

from app.db.models import Accessory, Board, CompatRule
from app.db.seed import ACCESSORIES_PATH, BOARDS_PATH, seed
from app.db.session import session_scope
from app.schemas import BoardCard


def _tmp_db_url(tmp_path: Path, name: str = "test.sqlite3") -> str:
    return f"sqlite:///{tmp_path / name}"


def test_seed_empty_db_yields_fixture_counts(tmp_path: Path) -> None:
    db_url = _tmp_db_url(tmp_path)
    boards_data = json.loads(BOARDS_PATH.read_text())
    accessories_data = json.loads(ACCESSORIES_PATH.read_text())

    with session_scope(db_url) as session:
        seed(session)

    with session_scope(db_url) as session:
        boards = session.execute(select(Board)).scalars().all()
        accessories = session.execute(select(Accessory)).scalars().all()
        rules = session.execute(select(CompatRule)).scalars().all()

    assert len(boards) == len(boards_data["boards"])
    assert len(accessories) == len(accessories_data["accessories"])
    assert len(rules) == len(accessories_data["compat_overrides"])


def test_seed_twice_is_idempotent(tmp_path: Path) -> None:
    db_url = _tmp_db_url(tmp_path)
    boards_data = json.loads(BOARDS_PATH.read_text())
    accessories_data = json.loads(ACCESSORIES_PATH.read_text())

    with session_scope(db_url) as session:
        seed(session)
    with session_scope(db_url) as session:
        seed(session)

    with session_scope(db_url) as session:
        boards = session.execute(select(Board)).scalars().all()
        accessories = session.execute(select(Accessory)).scalars().all()
        rules = session.execute(select(CompatRule)).scalars().all()

    assert len(boards) == len(boards_data["boards"])
    assert len(accessories) == len(accessories_data["accessories"])
    assert len(rules) == len(accessories_data["compat_overrides"])


def test_seeded_board_round_trips_field_values(tmp_path: Path) -> None:
    db_url = _tmp_db_url(tmp_path)
    boards_data = json.loads(BOARDS_PATH.read_text())
    sample = boards_data["boards"][0]

    with session_scope(db_url) as session:
        seed(session)

    with session_scope(db_url) as session:
        board = session.get(Board, sample["id"])
        assert board is not None
        assert board.id == sample["id"]
        assert board.brand == sample["brand"]
        assert board.model == sample["model"]
        assert board.length_ft == sample["length_ft"]
        assert board.width_in == sample["width_in"]
        assert board.thickness_in == sample["thickness_in"]
        assert board.volume_l == sample["volume_l"]
        assert board.max_rider_weight_kg == sample["max_rider_weight_kg"]
        assert board.recommended_psi == sample["recommended_psi"]
        assert board.max_psi == sample["max_psi"]
        assert board.board_type == sample["board_type"]
        assert board.skill_level == sample["skill_level"]
        assert board.fin_box == sample["fin_box"]
        assert board.valve_type == sample["valve_type"]
        assert board.board_weight_kg == sample["board_weight_kg"]
        assert board.price_usd == sample["price_usd"]
        assert board.best_for == sample["best_for"]
        assert board.image_url == sample["image_url"]
        assert board.is_mock == sample["is_mock"]


def test_seeded_board_row_validates_directly_as_board_card(tmp_path: Path) -> None:
    """`BoardCard.model_validate(row)` must work straight off a seeded ORM row

    (BoardCard has `from_attributes=True` specifically so S5/S7 can do this).
    """
    db_url = _tmp_db_url(tmp_path)
    boards_data = json.loads(BOARDS_PATH.read_text())
    sample = boards_data["boards"][0]

    with session_scope(db_url) as session:
        seed(session)

    with session_scope(db_url) as session:
        board = session.get(Board, sample["id"])
        assert board is not None
        card = BoardCard.model_validate(board)
        assert card.id == sample["id"]
        assert card.best_for == sample["best_for"]


def test_seeded_compat_rule_round_trips_from_override(tmp_path: Path) -> None:
    db_url = _tmp_db_url(tmp_path)
    accessories_data = json.loads(ACCESSORIES_PATH.read_text())
    sample = accessories_data["compat_overrides"][0]

    with session_scope(db_url) as session:
        seed(session)

    with session_scope(db_url) as session:
        rule = session.execute(
            select(CompatRule).where(
                CompatRule.board_id == sample["board_id"],
                CompatRule.accessory_id == sample["accessory_id"],
            )
        ).scalar_one()
        assert rule.compatible == sample["compatible"]
        assert rule.reason == sample["reason"]
        assert rule.caveats == sample["caveats"]
        assert rule.is_mock == sample["is_mock"]
