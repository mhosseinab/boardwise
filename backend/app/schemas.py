"""Frozen Pydantic v2 wire contracts for BoardWise (plan §5).

RULE (rule §4.8): this file freezes after S4. Later steps import these models but
must never edit them. Field names/types were chosen deliberately because
`frontend/src/lib/types.ts` hand-mirrors them field-for-field at S14.

Deliberate cross-step pins (CARRY-FORWARD for S2/S3/S5-S7/S14):
- Board/accessory ids are `str` slugs (e.g. "aquara-atlas-12"), not ints.
- `recommended_psi` / `max_psi` are `int` (whole PSI values); all other board
  measurements (`length_ft`, `width_in`, `thickness_in`, `volume_l`,
  `max_rider_weight_kg`, `board_weight_kg`, `price_usd`) are `float`.
- `board_type`, `skill_level`, `fin_box`, `valve_type` are plain `str` (not
  `Literal`), decoupled from the value-set S2/S3 own.
- `BoardCard` sets `model_config = ConfigDict(from_attributes=True)` so S5/S7 can
  build it directly from a SQLAlchemy ORM row via `BoardCard.model_validate(row)`.
- `SpecTable.rows` is `list[list[str]]`, one row per board, cells aligned to
  `columns` (already stringified/formatted for direct rendering).
- `ChatResponse.cards` / `.tables` / `.compatibility` / `.tools_used` default to
  empty lists (the refusal case populates none of them).
"""

from pydantic import BaseModel, ConfigDict, Field


class BoardCard(BaseModel):
    """The UI-facing subset of a `boards` row (SPEC "Backend requirements" #1)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    brand: str
    model: str
    length_ft: float
    width_in: float
    thickness_in: float
    volume_l: float
    max_rider_weight_kg: float
    recommended_psi: int
    max_psi: int
    board_type: str
    skill_level: str
    fin_box: str
    valve_type: str
    board_weight_kg: float
    price_usd: float
    best_for: list[str]
    image_url: str
    is_mock: bool = True


class SpecTable(BaseModel):
    title: str
    columns: list[str]
    rows: list[list[str]]
    board_ids: list[str]


class CompatibilityResult(BaseModel):
    board_id: str
    accessory_id: str
    compatible: bool
    reason: str
    caveats: list[str] = Field(default_factory=list)


class ToolCall(BaseModel):
    name: str
    args: dict
    result_summary: str
    latency_ms: int


class ChatRequest(BaseModel):
    message: str
    history: list | None = None


class ChatResponse(BaseModel):
    answer: str
    cards: list[BoardCard] = Field(default_factory=list)
    tables: list[SpecTable] = Field(default_factory=list)
    compatibility: list[CompatibilityResult] = Field(default_factory=list)
    tools_used: list[ToolCall] = Field(default_factory=list)
    refused: bool = False
    prompt_version: str
