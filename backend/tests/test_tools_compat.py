"""Tests for the S6 tools (app.agent.tools): `check_compatibility` and
`recommend_setup`, run against a tmp-path seeded SQLite DB (same fixture
pattern as `test_tools_lookup.py` / `test_seed.py`).
"""

import json
from pathlib import Path

from app.agent.tools import check_compatibility, recommend_setup
from app.db.seed import ACCESSORIES_PATH, seed
from app.db.session import session_scope


def _tmp_db_url(tmp_path: Path, name: str = "test.sqlite3") -> str:
    return f"sqlite:///{tmp_path / name}"


def _seeded_db_url(tmp_path: Path) -> str:
    db_url = _tmp_db_url(tmp_path)
    with session_scope(db_url) as session:
        seed(session)
    return db_url


def _compat_overrides() -> list[dict]:
    data = json.loads(ACCESSORIES_PATH.read_text())
    overrides: list[dict] = data["compat_overrides"]
    return overrides


# --- check_compatibility: seeded incompatible overrides ---------------------


def test_check_compatibility_seeded_overrides_are_incompatible(
    tmp_path: Path,
) -> None:
    db_url = _seeded_db_url(tmp_path)
    overrides = _compat_overrides()
    assert len(overrides) == 3  # sanity: matches the CARRY-FORWARD from S3

    for override in overrides:
        result = check_compatibility(
            override["board_id"], override["accessory_id"], database_url=db_url
        )
        assert result.board_id == override["board_id"]
        assert result.accessory_id == override["accessory_id"]
        assert result.compatible is False
        # Exact override reason wins over the in-code verdict — this is the
        # thing that proves the override path (not just code agreement).
        assert result.reason == override["reason"]
        assert result.caveats == override["caveats"]


def test_check_compatibility_fin_mismatch_override_matches_json(
    tmp_path: Path,
) -> None:
    db_url = _seeded_db_url(tmp_path)

    result = check_compatibility("brd-001", "fin-002", database_url=db_url)

    assert result.compatible is False
    assert result.reason == (
        "fin-box mismatch: RaceBlade is click-fit, but the Aquara Horizon "
        "11'0\" requires a US-box fin"
    )


# --- check_compatibility: known-good pairing ---------------------------------


def test_check_compatibility_known_good_fin_pairing_is_compatible(
    tmp_path: Path,
) -> None:
    db_url = _seeded_db_url(tmp_path)

    # brd-001 (Aquara Horizon) is US-box; fin-003 (Zephyr RiverRunner) is
    # also US-box, and no override exists for this pair.
    result = check_compatibility("brd-001", "fin-003", database_url=db_url)

    assert result.board_id == "brd-001"
    assert result.accessory_id == "fin-003"
    assert result.compatible is True
    assert result.reason != ""


def test_check_compatibility_known_good_pump_pairing_is_compatible(
    tmp_path: Path,
) -> None:
    db_url = _seeded_db_url(tmp_path)

    # brd-001 recommends 13 PSI on an H3 valve; pump-001 reaches 20 PSI on H3.
    result = check_compatibility("brd-001", "pump-001", database_url=db_url)

    assert result.compatible is True


# --- check_compatibility: caveat case (paddle) -------------------------------


def test_check_compatibility_paddle_is_compatible_with_height_caveat(
    tmp_path: Path,
) -> None:
    db_url = _seeded_db_url(tmp_path)

    result = check_compatibility("brd-001", "paddle-001", database_url=db_url)

    assert result.compatible is True
    assert result.caveats != []
    assert "height" in result.caveats[0].lower()


# --- check_compatibility: unknown ids ----------------------------------------


def test_check_compatibility_unknown_board_is_incompatible(tmp_path: Path) -> None:
    db_url = _seeded_db_url(tmp_path)

    result = check_compatibility("brd-does-not-exist", "fin-001", database_url=db_url)

    assert result.compatible is False


def test_check_compatibility_unknown_accessory_is_incompatible(
    tmp_path: Path,
) -> None:
    db_url = _seeded_db_url(tmp_path)

    result = check_compatibility("brd-001", "fin-does-not-exist", database_url=db_url)

    assert result.compatible is False


# --- recommend_setup ----------------------------------------------------------


def test_recommend_setup_95kg_beginner_respects_capacity_and_budget(
    tmp_path: Path,
) -> None:
    db_url = _seeded_db_url(tmp_path)

    bundle = recommend_setup(
        {
            "weight_kg": 95,
            "height_cm": 175,
            "skill_level": "beginner",
            "use_case": "touring",
            "budget_usd": 700,
        },
        database_url=db_url,
    )

    assert bundle is not None
    assert bundle["board"].skill_level == "beginner"
    assert bundle["board"].max_rider_weight_kg >= 95
    assert bundle["board"].price_usd <= 700
    # Deterministic pick given the seeded data: brd-001 is the only beginner
    # touring board within capacity and budget.
    assert bundle["board"].id == "brd-001"


def test_recommend_setup_bundle_accessories_all_pass_check_compatibility(
    tmp_path: Path,
) -> None:
    db_url = _seeded_db_url(tmp_path)

    bundle = recommend_setup(
        {
            "weight_kg": 95,
            "height_cm": 175,
            "skill_level": "beginner",
            "use_case": "touring",
            "budget_usd": 700,
        },
        database_url=db_url,
    )

    assert bundle is not None
    board_id = bundle["board"].id
    for accessory_type in ("paddle", "pump", "fin", "leash"):
        pick = bundle[accessory_type]  # type: ignore[literal-required]
        result = check_compatibility(board_id, pick["id"], database_url=db_url)
        assert result.compatible is True, (
            f"{accessory_type} pick {pick['id']} failed check_compatibility: "
            f"{result.reason}"
        )
    # `compatibility` on the bundle mirrors the same verdicts.
    assert len(bundle["compatibility"]) == 4
    assert all(c.compatible for c in bundle["compatibility"])


def test_recommend_setup_deterministic_accessory_ties_break_by_price_then_id(
    tmp_path: Path,
) -> None:
    db_url = _seeded_db_url(tmp_path)

    bundle = recommend_setup(
        {
            "weight_kg": 95,
            "height_cm": 175,
            "skill_level": "beginner",
            "use_case": "touring",
            "budget_usd": 700,
        },
        database_url=db_url,
    )

    assert bundle is not None
    # Two paddles fit a 175cm rider (paddle-001 $89, paddle-002 $249); the
    # cheaper one wins.
    assert bundle["paddle"]["id"] == "paddle-001"
    # fin-001 ($29) and fin-003 ($25) both match brd-001's US-box fin_box;
    # the cheaper one wins.
    assert bundle["fin"]["id"] == "fin-003"
    # leash-001 ($22) and leash-003 ($24) both suit touring; the cheaper one
    # wins.
    assert bundle["leash"]["id"] == "leash-001"
    # pump-001 is the only pump matching brd-001's 13 PSI / H3 valve needs.
    assert bundle["pump"]["id"] == "pump-001"


def test_recommend_setup_no_matching_board_returns_none(tmp_path: Path) -> None:
    db_url = _seeded_db_url(tmp_path)

    bundle = recommend_setup(
        {
            "weight_kg": 95,
            "height_cm": 175,
            "skill_level": "beginner",
            "use_case": "touring",
            "budget_usd": 1,
        },
        database_url=db_url,
    )

    assert bundle is None
