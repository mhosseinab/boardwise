"""Typed lookup tools for the BoardWise agent (S5): `get_board` and
`search_boards`. Plain, typed functions — no LangChain wrappers here; S11
wraps these as LangChain tools.

Rule (typed contracts): both functions return `app.schemas` models built via
`BoardCard.model_validate(row)`, never raw ORM rows (`app.db.models.Board`
column names match `BoardCard` field-for-field for exactly this purpose, see
`app/db/models.py`).

DB access (CARRY-FORWARD from S3): both functions default to the
env-configured `DATABASE_URL` via `app.db.session.session_scope`, but accept
an explicit `database_url` so tests (and later, ad-hoc scripts) can point
them at an isolated tmp SQLite file without touching global state.
"""

from typing import TypedDict

from sqlalchemy import ColumnElement, select

from app.db.models import Board
from app.db.session import session_scope
from app.schemas import BoardCard


class BoardSearchFilters(TypedDict, total=False):
    """Optional `search_boards` filters (SPEC "Backend requirements" item 2).

    All keys are optional; omitted keys are not filtered on. `min_capacity_kg`
    uses `>=` semantics against `max_rider_weight_kg` (a rider must fit under
    the board's capacity, not exactly match it).
    """

    board_type: str
    skill_level: str
    min_capacity_kg: float
    min_price_usd: float
    max_price_usd: float
    min_length_ft: float
    max_length_ft: float


def get_board(board_id: str, database_url: str | None = None) -> BoardCard | None:
    """Look up one board by its catalog id.

    Returns `None` if `board_id` is not in the catalog.
    """
    with session_scope(database_url) as session:
        row = session.get(Board, board_id)
        if row is None:
            return None
        return BoardCard.model_validate(row)


def search_boards(
    filters: BoardSearchFilters, database_url: str | None = None
) -> list[BoardCard]:
    """Search the catalog, honoring every key present in `filters`.

    Results are deterministically ordered (ascending by `id`) so the same
    filters always return the same sequence.
    """
    conditions: list[ColumnElement[bool]] = []
    if "board_type" in filters:
        conditions.append(Board.board_type == filters["board_type"])
    if "skill_level" in filters:
        conditions.append(Board.skill_level == filters["skill_level"])
    if "min_capacity_kg" in filters:
        conditions.append(Board.max_rider_weight_kg >= filters["min_capacity_kg"])
    if "min_price_usd" in filters:
        conditions.append(Board.price_usd >= filters["min_price_usd"])
    if "max_price_usd" in filters:
        conditions.append(Board.price_usd <= filters["max_price_usd"])
    if "min_length_ft" in filters:
        conditions.append(Board.length_ft >= filters["min_length_ft"])
    if "max_length_ft" in filters:
        conditions.append(Board.length_ft <= filters["max_length_ft"])

    query = select(Board).where(*conditions).order_by(Board.id)
    with session_scope(database_url) as session:
        rows = session.execute(query).scalars().all()
        return [BoardCard.model_validate(row) for row in rows]
