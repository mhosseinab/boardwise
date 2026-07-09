# BoardWise tool descriptions (v1)

These four tools are the agent's only way to touch product data. Every spec or number in an
answer must trace back to one of these tool results (see system_v1.md). The signatures below
match the functions to be implemented in `backend/app/agent/tools.py` (S5/S6 — not built yet).

## get_board

`get_board(board_id: str) -> BoardCard | None`

Look up one board by its catalog id and return its full spec row: brand, model, dimensions
(length/width/thickness/volume), max rider weight, recommended and max PSI, board type, skill
level, fin box, price, and best-for tags. Returns nothing if the id is not in the catalog. Use
this when the user names a specific board or you already know the id from a prior search.

## search_boards

`search_boards(filters: dict) -> list[BoardCard]`

Search the catalog by board_type, skill_level, minimum rider capacity
(max_rider_weight_kg >= X), price range, and length range. Use this when the user describes
what they need (a type, a skill level, a weight to carry, a budget) rather than naming a board
directly. Returns a deterministically ordered list of matching boards; may be empty.

## check_compatibility

`check_compatibility(board_id: str, accessory_id: str) -> CompatibilityResult`

Evaluate whether a given accessory (paddle, pump, fin, or leash) fits a given board, applying
the fitment rules for that accessory type (fin-box match, pump PSI/valve match, leash suited to
board type, paddle suited to rider height) plus any explicit override rule in the catalog.
Returns a typed compatible/incompatible verdict with a reason and any caveats. Use this whenever
the user asks if a specific accessory works with a specific board.

## recommend_setup

`recommend_setup(rider_profile: dict) -> dict`

Given a rider profile (`weight_kg`, `height_cm`, `skill_level`, `use_case`, optional
`budget_usd`), pick one suitable board (capacity, skill, and use-case match, within budget if
given) plus a compatible paddle, pump, fin, and leash, each with a one-line rationale. Use this
for "what setup should I get" style requests instead of chaining the other tools by hand.
