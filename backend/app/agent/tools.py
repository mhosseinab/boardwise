"""Typed lookup tools for the BoardWise agent: `get_board` and `search_boards`
(S5), plus `check_compatibility` and `recommend_setup` (S6). Plain, typed
functions — no LangChain wrappers here; S11 wraps these as LangChain tools.

Rule (typed contracts): all four functions return `app.schemas` models (or,
for `recommend_setup`'s bundle — which has no frozen schema — a local
`TypedDict`), never raw ORM rows (`app.db.models.Board` column names match
`BoardCard` field-for-field for exactly this purpose, see `app/db/models.py`).

DB access (CARRY-FORWARD from S3): all four functions default to the
env-configured `DATABASE_URL` via `app.db.session.session_scope`, but accept
an explicit `database_url` so tests (and later, ad-hoc scripts) can point
them at an isolated tmp SQLite file without touching global state.

S6 compatibility rules (SPEC "Backend requirements" item 2, decision §4.6):
the four fitment families live in code as `_fin_verdict` / `_pump_verdict` /
`_leash_verdict` / `_paddle_verdict`; an explicit `CompatRule` row for the
exact `(board_id, accessory_id)` pair — seeded from
`sample_data/accessories.json`'s `compat_overrides` — always wins over the
in-code verdict when one exists. Note the paddle rule: `check_compatibility`'s
frozen signature has no rider-height parameter (a paddle isn't paired to a
*board* by height, a *rider* is), so a paddle is never rejected for a board;
it always returns `compatible=True` with a caveat naming its height range —
this is the tool's one source of non-empty caveats absent an override.
"""

from typing import TypedDict

from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session

from app.db.models import Accessory, Board, CompatRule
from app.db.session import session_scope
from app.schemas import BoardCard, CompatibilityResult


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


# --- S6: check_compatibility -----------------------------------------------

_Verdict = tuple[bool, str, list[str]]


def _fin_verdict(board: Board, accessory: Accessory) -> _Verdict:
    if accessory.fin_box == board.fin_box:
        return (
            True,
            f"{accessory.model} is a {accessory.fin_box} fin, matching the "
            f"{board.brand} {board.model}'s {board.fin_box} fin box",
            [],
        )
    return (
        False,
        f"fin-box mismatch: {accessory.model} is {accessory.fin_box}, but "
        f"the {board.brand} {board.model} requires a {board.fin_box} fin",
        [],
    )


def _pump_verdict(board: Board, accessory: Accessory) -> _Verdict:
    max_psi = accessory.max_psi or 0
    psi_ok = max_psi >= board.recommended_psi
    valve_ok = accessory.valve_type == board.valve_type
    if psi_ok and valve_ok:
        return (
            True,
            f"{accessory.model} reaches {max_psi} PSI on a "
            f"{accessory.valve_type} valve, meeting the "
            f"{board.brand} {board.model}'s {board.recommended_psi} PSI / "
            f"{board.valve_type} valve requirement",
            [],
        )
    problems = []
    if not psi_ok:
        problems.append(
            f"under-spec pump: {accessory.model} tops out at {max_psi} PSI, "
            f"below the {board.brand} {board.model}'s recommended "
            f"{board.recommended_psi} PSI"
        )
    if not valve_ok:
        problems.append(
            f"valve mismatch: {accessory.model} uses a "
            f"{accessory.valve_type} valve, but the {board.brand} "
            f"{board.model} needs {board.valve_type}"
        )
    return False, "; ".join(problems), []


def _leash_verdict(board: Board, accessory: Accessory) -> _Verdict:
    suited = accessory.suited_board_types or []
    if board.board_type in suited:
        return (
            True,
            f"{accessory.model} is rated for {', '.join(suited)} boards, "
            f"which covers the {board.brand} {board.model} "
            f"({board.board_type})",
            [],
        )
    return (
        False,
        f"wrong-use leash: {accessory.model} is suited to "
        f"{', '.join(suited) or 'no listed board types'}, not "
        f"{board.board_type}",
        [],
    )


def _paddle_verdict(board: Board, accessory: Accessory) -> _Verdict:
    # Paddle fit depends on the paddler's height, not the board, and
    # `check_compatibility`'s frozen signature carries no rider height — so a
    # paddle is never rejected for pairing with a given board. The height
    # range is surfaced as a caveat so the caller still checks it manually.
    return (
        True,
        f"{accessory.model} mounts on any board; fit depends on paddler "
        f"height, not the {board.brand} {board.model}",
        [
            f"sized for paddlers {accessory.min_height_cm:.0f}-"
            f"{accessory.max_height_cm:.0f} cm tall — confirm against the "
            "paddler's height before buying"
        ],
    )


_VERDICT_BY_ACCESSORY_TYPE = {
    "fin": _fin_verdict,
    "pump": _pump_verdict,
    "leash": _leash_verdict,
    "paddle": _paddle_verdict,
}


def _evaluate_compatibility(
    session: Session, board: Board, accessory: Accessory
) -> CompatibilityResult:
    """Compute the in-code verdict for `(board, accessory)`, then apply an
    explicit `CompatRule` override for this exact pair if one is seeded.
    """
    verdict_fn = _VERDICT_BY_ACCESSORY_TYPE.get(accessory.type)
    compatible: bool
    reason: str
    caveats: list[str]
    if verdict_fn is None:
        compatible, reason, caveats = (
            False,
            f"unknown accessory type '{accessory.type}'",
            [],
        )
    else:
        compatible, reason, caveats = verdict_fn(board, accessory)

    override = session.execute(
        select(CompatRule).where(
            CompatRule.board_id == board.id,
            CompatRule.accessory_id == accessory.id,
        )
    ).scalar_one_or_none()
    if override is not None:
        compatible, reason, caveats = (
            override.compatible,
            override.reason,
            list(override.caveats),
        )

    return CompatibilityResult(
        board_id=board.id,
        accessory_id=accessory.id,
        compatible=compatible,
        reason=reason,
        caveats=caveats,
    )


def check_compatibility(
    board_id: str, accessory_id: str, database_url: str | None = None
) -> CompatibilityResult:
    """Evaluate whether `accessory_id` fits `board_id`.

    Applies the fitment rule for the accessory's type (fin-box match, pump
    PSI/valve match, leash suited to board type, paddle — always compatible
    with a height-range caveat), then an explicit `CompatRule` override for
    this exact pair if one exists in the catalog. If either id is unknown,
    returns `compatible=False` with a reason saying so.
    """
    with session_scope(database_url) as session:
        board = session.get(Board, board_id)
        accessory = session.get(Accessory, accessory_id)
        if board is None or accessory is None:
            return CompatibilityResult(
                board_id=board_id,
                accessory_id=accessory_id,
                compatible=False,
                reason="board or accessory id not found in catalog",
                caveats=[],
            )
        return _evaluate_compatibility(session, board, accessory)


# --- S6: recommend_setup -----------------------------------------------


class _RequiredRiderProfile(TypedDict):
    weight_kg: float
    height_cm: float
    skill_level: str
    use_case: str


class RiderProfile(_RequiredRiderProfile, total=False):
    """`recommend_setup` input (SPEC "Backend requirements" item 2).

    `budget_usd` is the only optional key; when omitted, price is not a
    filtering criterion.
    """

    budget_usd: float


class AccessoryPick(TypedDict):
    """One accessory chosen for a `recommend_setup` bundle."""

    id: str
    type: str
    brand: str
    model: str
    price_usd: float
    rationale: str


class SetupBundle(TypedDict):
    """`recommend_setup`'s return shape: one board plus one of each
    accessory type, all mutually compatible, with the compatibility
    verdicts that prove it.
    """

    board: BoardCard
    paddle: AccessoryPick
    pump: AccessoryPick
    fin: AccessoryPick
    leash: AccessoryPick
    compatibility: list[CompatibilityResult]


def _matches_use_case(board: Board, use_case: str) -> bool:
    needle = use_case.lower()
    if board.board_type.lower() == needle:
        return True
    return any(needle in tag.lower() for tag in board.best_for)


def _to_pick(accessory: Accessory, rationale: str) -> AccessoryPick:
    return AccessoryPick(
        id=accessory.id,
        type=accessory.type,
        brand=accessory.brand,
        model=accessory.model,
        price_usd=accessory.price_usd,
        rationale=rationale,
    )


def recommend_setup(
    rider_profile: RiderProfile, database_url: str | None = None
) -> SetupBundle | None:
    """Recommend one board plus a compatible paddle/pump/fin/leash bundle.

    The board must match `skill_level` exactly, carry capacity
    (`max_rider_weight_kg`) at least `weight_kg`, fit within `budget_usd`
    when given, and match `use_case` (against `board_type` or any
    `best_for` tag). Each accessory is chosen from the accessories that
    pass `check_compatibility` against the chosen board (the paddle is
    additionally narrowed to `height_cm`, since a paddle's board-level
    verdict is always compatible — see `_paddle_verdict`). Ties are broken
    deterministically: lowest `price_usd`, then `id`.

    Returns `None` if no board matches, or no accessory of some type is
    compatible with the chosen board.
    """
    with session_scope(database_url) as session:
        board_conditions: list[ColumnElement[bool]] = [
            Board.skill_level == rider_profile["skill_level"],
            Board.max_rider_weight_kg >= rider_profile["weight_kg"],
        ]
        budget_usd = rider_profile.get("budget_usd")
        if budget_usd is not None:
            board_conditions.append(Board.price_usd <= budget_usd)

        board_rows = (
            session.execute(
                select(Board)
                .where(*board_conditions)
                .order_by(Board.price_usd, Board.id)
            )
            .scalars()
            .all()
        )
        board = next(
            (b for b in board_rows if _matches_use_case(b, rider_profile["use_case"])),
            None,
        )
        if board is None:
            return None

        height_cm = rider_profile["height_cm"]
        paddle = (
            session.execute(
                select(Accessory)
                .where(
                    Accessory.type == "paddle",
                    Accessory.min_height_cm <= height_cm,
                    Accessory.max_height_cm >= height_cm,
                )
                .order_by(Accessory.price_usd, Accessory.id)
            )
            .scalars()
            .first()
        )
        pump = (
            session.execute(
                select(Accessory)
                .where(
                    Accessory.type == "pump",
                    Accessory.max_psi >= board.recommended_psi,
                    Accessory.valve_type == board.valve_type,
                )
                .order_by(Accessory.price_usd, Accessory.id)
            )
            .scalars()
            .first()
        )
        fin = (
            session.execute(
                select(Accessory)
                .where(Accessory.type == "fin", Accessory.fin_box == board.fin_box)
                .order_by(Accessory.price_usd, Accessory.id)
            )
            .scalars()
            .first()
        )
        leash_candidates = (
            session.execute(
                select(Accessory)
                .where(Accessory.type == "leash")
                .order_by(Accessory.price_usd, Accessory.id)
            )
            .scalars()
            .all()
        )
        leash = next(
            (
                a
                for a in leash_candidates
                if board.board_type in (a.suited_board_types or [])
            ),
            None,
        )

        if paddle is None or pump is None or fin is None or leash is None:
            return None

        picks = {
            "paddle": (
                paddle,
                f"fits paddlers {paddle.min_height_cm:.0f}-"
                f"{paddle.max_height_cm:.0f} cm, covering the rider's "
                f"{height_cm:.0f} cm height",
            ),
            "pump": (
                pump,
                f"reaches {pump.max_psi} PSI on a {pump.valve_type} valve, "
                f"meeting the board's {board.recommended_psi} PSI / "
                f"{board.valve_type} valve needs",
            ),
            "fin": (
                fin,
                f"{fin.fin_box} fin matches the board's {board.fin_box} " "fin box",
            ),
            "leash": (
                leash,
                f"rated for {board.board_type} use",
            ),
        }
        compatibility = [
            _evaluate_compatibility(session, board, accessory)
            for accessory, _ in picks.values()
        ]

        return SetupBundle(
            board=BoardCard.model_validate(board),
            paddle=_to_pick(*picks["paddle"]),
            pump=_to_pick(*picks["pump"]),
            fin=_to_pick(*picks["fin"]),
            leash=_to_pick(*picks["leash"]),
            compatibility=compatibility,
        )
