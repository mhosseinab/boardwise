"""BoardWise FastAPI app (S7): the browsable-catalog endpoints. S12 adds
`POST /api/chat`, wiring the S12 pipeline (backstop -> agent -> grounding ->
assembled response) into this same app object.

Rule (typed contracts): every response here is a frozen `app.schemas` model
(or a plain dict for `/api/health`) — the server never emits markup, and
these handlers never touch the DB directly, only via the S5 lookup tools
(`app.agent.tools.get_board` / `search_boards`) or, for `/api/chat`, the S12
pipeline.

CARRY-FORWARD for S13 (adds `/api/metrics` next): keep new routes as plain
`@app.get`/`@app.post` handlers here, reusing the `lifespan` startup seed
hook already wired up below.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query

from app.agent.pipeline import handle_chat
from app.agent.tools import BoardSearchFilters, get_board, search_boards
from app.db.seed import seed
from app.db.session import session_scope
from app.schemas import BoardCard, ChatRequest, ChatResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run the idempotent seeder against the env-configured `DATABASE_URL`."""
    with session_scope() as session:
        seed(session)
    yield


app = FastAPI(title="BoardWise API", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/boards", response_model=list[BoardCard])
def list_boards(
    board_type: str | None = None,
    skill_level: str | None = None,
    min_capacity_kg: float | None = None,
    max_price_usd: float | None = None,
    min_length_ft: float | None = None,
    max_length_ft: float | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[BoardCard]:
    filters: BoardSearchFilters = {}
    if board_type is not None:
        filters["board_type"] = board_type
    if skill_level is not None:
        filters["skill_level"] = skill_level
    if min_capacity_kg is not None:
        filters["min_capacity_kg"] = min_capacity_kg
    if max_price_usd is not None:
        filters["max_price_usd"] = max_price_usd
    if min_length_ft is not None:
        filters["min_length_ft"] = min_length_ft
    if max_length_ft is not None:
        filters["max_length_ft"] = max_length_ft

    results = search_boards(filters)
    return results[offset : offset + limit]


@app.get("/api/boards/{board_id}", response_model=BoardCard)
def get_board_by_id(board_id: str) -> BoardCard:
    card = get_board(board_id)
    if card is None:
        raise HTTPException(status_code=404, detail="board not found")
    return card


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """The S12 pipeline entry point. `model` is left unset here (the
    injection point for tests lives in `handle_chat`/`run_agent`, per
    decision §4.9) so this route builds the real, env-configured model only
    when actually invoked — never during the offline test suite, which
    calls `handle_chat` directly with a fake model.
    """
    return handle_chat(request)
