"""SQLAlchemy 2.0 ORM models for BoardWise: `Board`, `Accessory`, `CompatRule`.

`Board`'s column names match `app.schemas.BoardCard`'s field names exactly
(same names, compatible types) so later steps can build a `BoardCard` straight
from a seeded row via `BoardCard.model_validate(board_row)` — `BoardCard` sets
`model_config = ConfigDict(from_attributes=True)` for this purpose (see
`app/schemas.py`, frozen at S4).

`Accessory` stores all four accessory types (fin/pump/leash/paddle) in one
table; only the shared columns (id, type, brand, model, price_usd, is_mock)
are required, and every type-specific column is nullable.

`CompatRule` mirrors `sample_data/accessories.json`'s `compat_overrides`: an
explicit override for a `(board_id, accessory_id)` pairing. Both foreign keys
are nullable so a future attribute-pattern rule (matching by fin_box/valve_type
rather than a specific id) can omit either side without a schema change
(decision plan §4.6: compat logic lives in code, overrides are data).
"""

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Board(Base):
    """A seeded stand-up-paddleboard row (SPEC "Backend requirements" #1)."""

    __tablename__ = "boards"

    id: Mapped[str] = mapped_column(primary_key=True)
    brand: Mapped[str]
    model: Mapped[str]
    length_ft: Mapped[float]
    width_in: Mapped[float]
    thickness_in: Mapped[float]
    volume_l: Mapped[float]
    max_rider_weight_kg: Mapped[float]
    recommended_psi: Mapped[int]
    max_psi: Mapped[int]
    board_type: Mapped[str]
    skill_level: Mapped[str]
    fin_box: Mapped[str]
    valve_type: Mapped[str]
    board_weight_kg: Mapped[float]
    price_usd: Mapped[float]
    best_for: Mapped[list[str]] = mapped_column(JSON)
    image_url: Mapped[str]
    is_mock: Mapped[bool] = mapped_column(default=True)


class Accessory(Base):
    """A seeded paddle/pump/fin/leash row; type-specific fields are nullable."""

    __tablename__ = "accessories"

    id: Mapped[str] = mapped_column(primary_key=True)
    type: Mapped[str]
    brand: Mapped[str]
    model: Mapped[str]
    price_usd: Mapped[float]
    is_mock: Mapped[bool] = mapped_column(default=True)

    # fin
    fin_box: Mapped[str | None] = mapped_column(default=None)
    # pump
    max_psi: Mapped[int | None] = mapped_column(default=None)
    valve_type: Mapped[str | None] = mapped_column(default=None)
    dual_stage: Mapped[bool | None] = mapped_column(default=None)
    # leash
    suited_board_types: Mapped[list[str] | None] = mapped_column(JSON, default=None)
    length_ft: Mapped[float | None] = mapped_column(default=None)
    style: Mapped[str | None] = mapped_column(default=None)
    # paddle
    min_height_cm: Mapped[float | None] = mapped_column(default=None)
    max_height_cm: Mapped[float | None] = mapped_column(default=None)
    adjustable: Mapped[bool | None] = mapped_column(default=None)


class CompatRule(Base):
    """An explicit board/accessory compatibility override row."""

    __tablename__ = "compat_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    board_id: Mapped[str | None] = mapped_column(ForeignKey("boards.id"), default=None)
    accessory_id: Mapped[str | None] = mapped_column(
        ForeignKey("accessories.id"), default=None
    )
    compatible: Mapped[bool]
    reason: Mapped[str]
    caveats: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_mock: Mapped[bool] = mapped_column(default=True)
