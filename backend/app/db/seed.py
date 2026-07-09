"""Idempotent seeder: loads `sample_data/*.json` into `boards`/`accessories`/
`compat_rules`.

Idempotency policy (load-bearing — later steps and CI rely on this): `seed()`
checks whether the `boards` table already has any rows and, if so, does
nothing. Running `python -m app.db.seed` (or calling `main()`) any number of
times against the same database therefore leaves row counts unchanged after
the first run.
"""

import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Accessory, Board, CompatRule
from app.db.session import session_scope

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SAMPLE_DATA_DIR = _REPO_ROOT / "sample_data"
BOARDS_PATH = _SAMPLE_DATA_DIR / "boards.json"
ACCESSORIES_PATH = _SAMPLE_DATA_DIR / "accessories.json"


def _load_json(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(path.read_text())
    return result


def _board_from_json(row: dict[str, Any]) -> Board:
    return Board(
        id=row["id"],
        brand=row["brand"],
        model=row["model"],
        length_ft=row["length_ft"],
        width_in=row["width_in"],
        thickness_in=row["thickness_in"],
        volume_l=row["volume_l"],
        max_rider_weight_kg=row["max_rider_weight_kg"],
        recommended_psi=row["recommended_psi"],
        max_psi=row["max_psi"],
        board_type=row["board_type"],
        skill_level=row["skill_level"],
        fin_box=row["fin_box"],
        valve_type=row["valve_type"],
        board_weight_kg=row["board_weight_kg"],
        price_usd=row["price_usd"],
        best_for=row["best_for"],
        image_url=row["image_url"],
        is_mock=row["is_mock"],
    )


def _accessory_from_json(row: dict[str, Any]) -> Accessory:
    return Accessory(
        id=row["id"],
        type=row["type"],
        brand=row["brand"],
        model=row["model"],
        price_usd=row["price_usd"],
        is_mock=row["is_mock"],
        fin_box=row.get("fin_box"),
        max_psi=row.get("max_psi"),
        valve_type=row.get("valve_type"),
        dual_stage=row.get("dual_stage"),
        suited_board_types=row.get("suited_board_types"),
        length_ft=row.get("length_ft"),
        style=row.get("style"),
        min_height_cm=row.get("min_height_cm"),
        max_height_cm=row.get("max_height_cm"),
        adjustable=row.get("adjustable"),
    )


def _compat_rule_from_json(row: dict[str, Any]) -> CompatRule:
    return CompatRule(
        board_id=row.get("board_id"),
        accessory_id=row.get("accessory_id"),
        compatible=row["compatible"],
        reason=row["reason"],
        caveats=row.get("caveats", []),
        is_mock=row["is_mock"],
    )


def seed(session: Session) -> None:
    """Populate `boards`/`accessories`/`compat_rules` from `sample_data/*.json`.

    No-op if `boards` already has rows (idempotent by design).
    """
    if session.execute(select(Board.id)).first() is not None:
        return

    boards_data = _load_json(BOARDS_PATH)
    accessories_data = _load_json(ACCESSORIES_PATH)

    session.add_all(_board_from_json(row) for row in boards_data["boards"])
    session.add_all(
        _accessory_from_json(row) for row in accessories_data["accessories"]
    )
    session.add_all(
        _compat_rule_from_json(row)
        for row in accessories_data.get("compat_overrides", [])
    )


def main() -> None:
    with session_scope() as session:
        seed(session)


if __name__ == "__main__":
    main()
