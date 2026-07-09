"""Tests for the sample_data catalog fixtures.

Validates that sample_data/boards.json and sample_data/accessories.json are
well-formed, cover every board_type and skill_level, encode at least three
deliberately incompatible accessory pairings, and never reference a real
stand-up-paddleboard brand (fictional-brands-only is a hard legal
constraint; see the project rules).
"""

import json
from pathlib import Path
from typing import Any

import pytest

SAMPLE_DATA_DIR = Path(__file__).resolve().parents[2] / "sample_data"
BOARDS_PATH = SAMPLE_DATA_DIR / "boards.json"
ACCESSORIES_PATH = SAMPLE_DATA_DIR / "accessories.json"

REQUIRED_BOARD_FIELDS = {
    "id",
    "brand",
    "model",
    "length_ft",
    "width_in",
    "thickness_in",
    "volume_l",
    "max_rider_weight_kg",
    "recommended_psi",
    "max_psi",
    "board_type",
    "skill_level",
    "fin_box",
    "valve_type",
    "board_weight_kg",
    "price_usd",
    "best_for",
    "image_url",
    "is_mock",
}

BOARD_TYPES = {"touring", "yoga", "whitewater", "racing", "all-around"}
SKILL_LEVELS = {"beginner", "intermediate", "advanced"}
ACCESSORY_TYPES = {"paddle", "pump", "fin", "leash"}

# Real SUP brands that must never appear in fixture text (case-insensitive).
REAL_SUP_BRANDS = [
    "Starboard",
    "Fanatic",
    "Naish",
    "Red Paddle",
    "iROCKER",
    "BOTE",
    "NIXY",
    "Thurso",
    "Bluefin",
    "Aqua Marina",
    "Hala",
    "SIC",
    "Tower",
    "Isle",
]


@pytest.fixture(scope="module")
def boards_data() -> dict[str, Any]:
    return json.loads(BOARDS_PATH.read_text())


@pytest.fixture(scope="module")
def accessories_data() -> dict[str, Any]:
    return json.loads(ACCESSORIES_PATH.read_text())


def test_boards_file_parses(boards_data: dict[str, Any]) -> None:
    assert isinstance(boards_data.get("boards"), list)


def test_accessories_file_parses(accessories_data: dict[str, Any]) -> None:
    assert isinstance(accessories_data.get("accessories"), list)


def test_both_files_carry_mock_note_header(
    boards_data: dict[str, Any], accessories_data: dict[str, Any]
) -> None:
    assert boards_data.get("_note") == "illustrative mock data"
    assert accessories_data.get("_note") == "illustrative mock data"


def test_board_count_in_range(boards_data: dict[str, Any]) -> None:
    assert 12 <= len(boards_data["boards"]) <= 15


def test_every_board_has_all_required_fields(boards_data: dict[str, Any]) -> None:
    for board in boards_data["boards"]:
        missing = REQUIRED_BOARD_FIELDS - board.keys()
        assert not missing, f"board {board.get('id')} missing fields: {missing}"


def test_every_board_is_marked_mock(boards_data: dict[str, Any]) -> None:
    for board in boards_data["boards"]:
        assert board["is_mock"] is True, f"board {board.get('id')} is not is_mock"


def test_every_board_type_appears(boards_data: dict[str, Any]) -> None:
    types_seen = {board["board_type"] for board in boards_data["boards"]}
    assert BOARD_TYPES <= types_seen


def test_every_skill_level_appears(boards_data: dict[str, Any]) -> None:
    levels_seen = {board["skill_level"] for board in boards_data["boards"]}
    assert SKILL_LEVELS <= levels_seen


def test_recommended_psi_never_exceeds_max_psi(boards_data: dict[str, Any]) -> None:
    for board in boards_data["boards"]:
        assert (
            board["recommended_psi"] <= board["max_psi"]
        ), f"board {board.get('id')} has recommended_psi > max_psi"


def test_accessories_cover_all_four_types(accessories_data: dict[str, Any]) -> None:
    types_seen = {item["type"] for item in accessories_data["accessories"]}
    assert ACCESSORY_TYPES <= types_seen


def test_every_accessory_is_marked_mock(accessories_data: dict[str, Any]) -> None:
    for item in accessories_data["accessories"]:
        assert item["is_mock"] is True, f"accessory {item.get('id')} is not is_mock"


def test_at_least_three_compat_overrides(accessories_data: dict[str, Any]) -> None:
    overrides = accessories_data.get("compat_overrides", [])
    assert len(overrides) >= 3
    for override in overrides:
        assert override["compatible"] is False
        assert override["reason"]
        assert override["is_mock"] is True, (
            f"compat_override {override.get('accessory_id')}/"
            f"{override.get('board_id')} is not is_mock"
        )


@pytest.mark.parametrize("brand", REAL_SUP_BRANDS)
def test_no_real_sup_brand_names_in_fixtures(
    brand: str, boards_data: dict[str, Any], accessories_data: dict[str, Any]
) -> None:
    haystack = (json.dumps(boards_data) + json.dumps(accessories_data)).lower()
    assert brand.lower() not in haystack, f"denylisted real brand found: {brand}"
