# Project 5 — BoardWise: A Domain-Constrained SUP Gear Expert Agent

> **How to use this file:** Paste everything below the line into your coding agent (Claude Code, Cursor, etc.) as a single build brief. It is self-contained. Assumptions I made to fill gaps are listed at the very bottom — change any you disagree with before running.

---

## Status

**Idea / spec — not started.** This is a build brief; no code exists yet. <!-- ASSUMED: no BoardWise repo has been created; update to "in-progress" once scaffolded. -->

## Problem & motivation

General-purpose LLM chatbots confidently invent product specifications — weight capacities, PSI ratings, prices — which makes them unusable for purchase decisions where a wrong number costs money or safety. The fix is architectural, not prompt-level: constrain the agent to one domain, force every claim through tools backed by a real database, and verify grounding in code after generation. BoardWise demonstrates that pattern end-to-end on a concrete vertical (SUP gear), with an eval harness that measures — rather than asserts — that the agent never fabricates a spec.

As a portfolio piece, it targets reviewers hiring for applied AI/LLM engineering: it proves tool-calling, structured outputs, guardrail enforcement, refusal behavior, and evals — the parts of vertical-agent work that generic chatbot demos skip.

## Role & objective

You are a senior AI/LLM engineer. Build a production-quality, open-source portfolio project called **BoardWise**: a friendly, consumer-facing chat app where a shopper asks questions about **stand-up paddleboards (SUP)** and gear, and a **strictly domain-constrained LangChain agent** answers by **calling tools against a structured product database** — never from memory. Every spec it states (weight capacity, recommended PSI, dimensions, fin-box type, price) must be **grounded in a tool result**, and the answers render inline as **rich product cards and spec/comparison tables**, not as a wall of model text.

This is the repo that proves you can build a **narrow, trustworthy vertical agent**: a tight system-prompt constraint, tool-calling grounded in real data, typed/structured outputs, honest refusals on out-of-domain questions, and an eval set that shows the agent **never invents a spec**. Optimize for a reviewer skimming for 90 seconds and a hiring manager cloning and running it in one command.

## Use case context

BoardWise is a **specialty SUP gear expert** — imagine the best salesperson in a paddlesports shop, available as a chat box. A shopper asks things like:

- "I'm 95 kg and new to paddling — which boards can actually carry me, and what should I inflate them to?"
- "Is the Fjord Glide fin compatible with the Aquara Atlas 12'0"?"
- "Compare the Riptide Tourer 11'6" and the Aquara Atlas 12'0" for a weekend touring trip."
- "Build me a complete beginner setup for flatwater under $900 — board, paddle, pump, fin, leash."

The agent answers about **weight/capacity limits, recommended inflation PSI, board dimensions, rider skill level, intended use (touring vs yoga vs whitewater vs racing), and accessory compatibility (paddles, pumps, fins, leashes)** — and recommends optimal setups by **cross-referencing specific board specifications**. It must **refuse or redirect** anything off-topic ("what's the weather," "write me a poem") and must say **"I don't have that spec"** rather than guessing when the database doesn't contain the answer.

> **Integrity note for whoever builds this — read this twice.** All product data is **synthetic and illustrative**. Use **fictionalized brand and model names** (e.g., *Aquara Atlas 12'0"*, *Riptide Tourer 11'6"*, *Fjord Glide*) — never real trademarks — and **never present invented numbers as the real specifications of a real commercial product**. The agent must ground every claim in the mock DB and must never fabricate a spec that isn't in it. Surface a visible "specs are mock data for demonstration" notice in **both** the UI and the README.

## Tech stack (pin these versions)

- **Frontend:** React 18 + TypeScript + Vite, Tailwind CSS, TanStack Query for data fetching, `react-markdown` for the answer prose only (specs render as typed components, never markdown).
- **Backend:** Python 3.11, FastAPI + Uvicorn, LangChain for the tool-calling agent, SQLAlchemy 2.0 over **SQLite** (zero-config, file-backed, seeded from a JSON fixture at startup), Pydantic v2 for typed contracts.
- **LLM access:** provider-agnostic via an OpenAI-compatible client configured through environment variables (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`). Must run against OpenAI, an Anthropic-compatible gateway, or a local function-calling model (Ollama/vLLM) with no code changes. Never hardcode a provider or key. The model must support tool/function calling.
- **Infra:** Docker + Docker Compose. **React on port 3006, FastAPI on port 8006.**

## Visual identity (make this project's look distinct)

This is the **one bright, warm, consumer-retail** repo in the set — the other four are all dark (emerald-on-green-black terminal, black-and-white lab, deep-monochrome SaaS, graphite IDE). **Lean all the way into light and friendly.** Do not reuse this look elsewhere.

- **Light theme.** Base background **off-white / sand `#F7F9FA`**, elevated card surfaces pure white `#FFFFFF`, hairline borders `#E5EBEE`.
- **Deep ocean-teal primary `#0E7C86`** for headers, links, and selected states, with **aqua accent `#14B8C4`** for highlights, tags, and the "thinking" shimmer. **Coral CTA `#FF6B5A`** for the primary action buttons (Send, "Build my setup") — used sparingly so it pops.
- **Compatibility semantics:** a small, consistent badge system — **compatible `#0E9F6E` (green)**, **not compatible `#EF4444` (red)**, **check fit / caveat `#F59E0B` (amber)**.
- **Typography:** a **friendly geometric sans** — `Poppins` for headings and product names, `Inter` for body and specs. Generous line-height. Numbers can stay in `Inter` with tabular figures inside spec tables.
- **Feel:** rounded corners (12–16px radius), **soft, diffuse shadows** (not hard borders), airy whitespace, rounded pill tags, gentle 180–220ms ease transitions. Approachable, calm, coastal — think a modern outdoor-gear DTC storefront, not a dev tool. A subtle sand-to-white vertical gradient on the page background is welcome.

## Architecture

```
Board catalog (JSON) ─► seed script ─► SQLite (boards, accessories, compat_rules)
                                             │
User question ─► POST /api/chat ─► CONSTRAINED LangChain agent (SUP expert ONLY)
                                             │  system prompt locks domain + "ground every spec"
                                             │  tools: get_board(id), search_boards(filters),
                                             │         check_compatibility(board, accessory),
                                             │         recommend_setup(rider_profile)
                                             ▼
                                   Typed tool results (rows straight from the DB)
                                             │
                          Grounding guardrail: every spec in the answer MUST trace
                          to a tool result — else it's stripped / "I don't have that spec"
                                             │
                          Structured payload: {answer, cards[], tables[], compatibility[], tools_used[]}
                                             ▼
        React renders PRODUCT CARDS + SPEC/COMPARISON TABLES + COMPAT BADGES inline
        (off-topic question ─► polite refusal, refused=true, zero tools run)
```

## Backend requirements

1. **Product database (SQLite, seeded from JSON).** Model three tables via SQLAlchemy: `boards`, `accessories`, and `compat_rules`. A `boards` row carries at minimum: `id`, `brand`, `model`, `length_ft`, `width_in`, `thickness_in`, `volume_l`, `max_rider_weight_kg`, `recommended_psi`, `max_psi`, `board_type` (`touring|yoga|whitewater|racing|all-around`), `skill_level` (`beginner|intermediate|advanced`), `fin_box` (e.g. `US-box|click-fit`), `valve_type` (e.g. `H3`), `board_weight_kg`, `price_usd`, `best_for` (list of tags), `image_url` (placeholder), and `is_mock: true`. Accessories cover **paddles, pumps, fins, leashes** with the fields each type needs to reason about fit. On startup, seed the DB from `sample_data/*.json` **idempotently** (only if empty). Ship a standalone `python -m app.db.seed` entry point too.
2. **The constrained agent — this is the headline engineering feature.** Build a LangChain **tool-calling agent** whose **system prompt strictly scopes it to SUP gear expertise** and forbids answering anything else. Give it exactly these tools, each backed by real DB queries:
   - `get_board(board_id)` → one board's full spec row.
   - `search_boards(filters)` → boards matching `board_type`, `skill_level`, `max_rider_weight_kg ≥ X`, price range, length range, etc.
   - `check_compatibility(board_id, accessory_id)` → evaluates the compat rules (fin matches `fin_box`; pump `max_psi ≥ board.recommended_psi` and valve match; leash suited to `board_type`; paddle within rider height range) and returns a typed result with a reason and caveats.
   - `recommend_setup(rider_profile)` → given `{weight_kg, height_cm, skill_level, use_case, budget_usd?}`, picks a suitable board then a compatible paddle/pump/fin/leash, returning the bundle with rationale.
   Cap the agent at **6 tool iterations**. Log every tool call, its args, and a result summary.
3. **Grounding guardrail — enforce in code, not just the prompt.** After the agent produces its answer, run a validator that ensures **every spec/number the answer asserts appears in the union of that turn's tool results**. If the model states a spec that wasn't returned by a tool, **strip it or replace it with "I don't have that spec in my catalog."** The agent must **never** surface a dimension, capacity, PSI, or price that didn't come from a tool. Document this mechanism prominently — it is the project's integrity story.
4. **Domain refusal.** If the question is out of domain (not about SUP gear), the agent returns a **polite refusal/redirect** (`refused: true`), runs **zero tools**, and offers to help with paddleboards instead. This behavior is prompt-driven **and** backstopped by a lightweight classifier check so a jailbreak can't drag it off-topic.
5. **Endpoints & typed contracts (Pydantic v2):**
   - `POST /api/chat` `{message, history?}` → `ChatResponse { answer: str, cards: list[BoardCard], tables: list[SpecTable], compatibility: list[CompatibilityResult], tools_used: list[ToolCall], refused: bool, prompt_version: str }`.
   - `GET /api/boards` with query filters (type, skill, max weight, price, length) → paginated `list[BoardCard]` for the browsable catalog.
   - `GET /api/boards/{id}` → one `BoardCard`.
   `BoardCard`, `SpecTable { title, columns, rows, board_ids }`, `CompatibilityResult { board_id, accessory_id, compatible: bool, reason, caveats: list[str] }`, and `ToolCall { name, args, result_summary, latency_ms }` are all typed models. The LLM emits **structured tool outputs → the server assembles these payloads → the UI renders them.** The model never emits raw JSX or HTML.
6. **Observability & guardrails:** structured JSON logs per request with latency, tools called, token counts, and estimated cost; trace the tool sequence into `tools_used` so the UI can show which tools ran. Expose `GET /api/health` and `GET /api/metrics` (request count, p50/p95 latency, refusal rate, avg tools/turn). Temperature 0 by default.

## Frontend requirements

- **Consumer-facing chat, not a dev tool.** Center column is a warm, roomy **chat thread**. The composer has a coral **Send** button and a rider-profile quick-fill (weight, height, skill, use). Above the empty thread, show 4–6 **example prompt chips** ("Beginner setup under $900," "Compare two touring boards," "Is this fin compatible?").
- **Rich in-chat rendering from the structured payload — never raw model text:**
  - **Product cards:** image placeholder, brand + model, a tidy key-spec strip (length, width, capacity, PSI, price), and **"best for" pill tags**. A card has an "Add to compare" affordance and links to the catalog detail.
  - **Spec comparison tables:** when the answer compares boards, render a clean side-by-side table from `SpecTable` with tabular figures and the winning cell subtly highlighted.
  - **Compatibility badges:** green/red/amber pill with the one-line reason and any caveats, rendered from `CompatibilityResult`.
- **Browsable catalog side panel:** a right (or slide-over) panel listing all boards with filters (type, skill, capacity, price) served by `GET /api/boards`; clicking a board can seed a chat question about it.
- **Mock-data notice:** a persistent, visible line — e.g. a small banner or footer — stating **"Specs are mock data for demonstration."**
- **States & a11y:** loading skeletons for cards/tables, a warm empty/first-run state, graceful error rendering, and a distinct **refusal** rendering (friendly "I only cover paddleboards" card). Fully keyboard navigable; respect `prefers-reduced-motion`.

## Data & fixtures

- Ship `sample_data/boards.json` with **~12–15 fictional boards** spanning every `board_type` and skill level, with realistic-but-invented specs and **clearly fictional brand/model names** (Aquara, Riptide, Zephyr, Cascade, Velocity, Fjord, etc.). Include a header/README note that these are illustrative.
- Ship `sample_data/accessories.json` with a set of **paddles, pumps, fins, and leashes** plus the fields that drive fit, and encode the **compatibility rules** (fin-box match, pump PSI/valve, leash-by-use, paddle-by-height) either as data or in `check_compatibility`. Provide at least a few deliberately **incompatible** pairings so the red/amber badges have something to show.
- Provide `sample_data/example_prompts.md` with 8–10 prompts that exercise search, single-board lookup, compatibility (both pass and fail), a full `recommend_setup`, a **missing-spec** case ("what's the warranty?" → "I don't have that spec"), and an **off-topic** case (→ refusal).

## AI-engineering rigor (this is what the target reviewer cares about)

- **Versioned prompts as assets** in `backend/app/prompts/` (system/domain-constraint prompt + tool descriptions), never inline strings. Stamp `prompt_version` on every response. Document the guardrails in a short `prompts/README.md`.
- **Eval harness** in `evals/`: a `cases.yaml` of labeled cases run by `run_evals.py` / `pytest`, scoring three things and printing a table:
  - **(a) Answer correctness vs DB ground truth** — the stated capacity/PSI/dimensions/compatibility match what the seeded DB actually says.
  - **(b) Grounding / faithfulness** — **no spec appears in the answer that isn't present in that turn's tool results** (the core anti-hallucination metric).
  - **(c) Out-of-domain refusal rate** — off-topic prompts are refused, in-domain prompts are answered.
  Add a `make eval` target. Log model + prompt version with every run.
- **Observability of tool calls:** every response carries `tools_used`, and eval output reports avg tools/turn and tool-error rate.
- **Determinism:** temperature 0, capped iterations, deterministic seed data so evals are stable and offline-repeatable with a mocked model.

## Repository structure

```
boardwise/
├── README.md
├── LICENSE                       # MIT
├── docker-compose.yml
├── .env.example
├── .github/workflows/ci.yml
├── Makefile
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml            # or requirements.txt + requirements-dev.txt
│   ├── app/
│   │   ├── main.py               # FastAPI app + routes
│   │   ├── agent/
│   │   │   ├── agent.py          # constrained tool-calling agent, iteration cap
│   │   │   ├── tools.py          # get_board, search_boards, check_compatibility, recommend_setup
│   │   │   └── guardrails.py     # grounding validator + domain-refusal backstop
│   │   ├── prompts/              # versioned system prompt + tool descriptions
│   │   ├── db/
│   │   │   ├── models.py         # SQLAlchemy: Board, Accessory, CompatRule
│   │   │   ├── session.py
│   │   │   └── seed.py           # JSON → SQLite seeder (idempotent)
│   │   ├── schemas.py            # Pydantic: BoardCard, SpecTable, CompatibilityResult, ChatResponse
│   │   └── observability.py
│   └── tests/                    # pytest: tools, grounding, refusal
├── evals/
│   ├── cases.yaml
│   └── run_evals.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── components/           # ChatPane, ProductCard, SpecTable, CompatBadge, CatalogPanel, ExamplePrompts
│       ├── lib/                  # api client, types mirrored from Pydantic
│       └── main.tsx
└── sample_data/
    ├── boards.json               # ~12–15 fictional boards
    ├── accessories.json          # paddles, pumps, fins, leashes + compat rules
    └── example_prompts.md
```

## Infrastructure

- `docker-compose.yml` with two services (`web` → **3006**, `api` → **8006**), healthchecks on both, and `.env` wiring. The `api` container seeds the SQLite DB on boot (idempotently) so `docker compose up` yields a fully working, populated app on the first run.
- Multi-stage Dockerfiles for small final images: frontend built and served as a static bundle behind a lightweight server; backend on Uvicorn with a sensible worker count. Run the API container as a non-root user.
- `.env.example` documenting `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_TEMPERATURE`, `MAX_TOOL_ITERATIONS`, `DATABASE_URL` (defaults to a local SQLite path).

## Testing

- **Backend (pytest):** tool correctness (`get_board` returns the seeded row; `search_boards` filters honor capacity/type/price; `check_compatibility` returns the right verdict for a matching fin-box, an under-spec pump, and a use-case-mismatched leash); Pydantic contract shape of `ChatResponse`. Then the two **signature tests**:
  - **Off-topic refusal test** — an out-of-domain prompt returns `refused: true`, runs **zero tools**, and does not answer.
  - **No-ungrounded-spec test** — feed a canned transcript where the model tries to assert a spec absent from tool results; assert the grounding guardrail strips it (answer contains **no** ungrounded number and instead says it lacks that spec).
  The LLM is **mocked** in unit tests via canned tool-call transcripts so CI stays offline and deterministic.
- **Frontend (Vitest + React Testing Library):** chat submit flow, `ProductCard` render from a mocked payload, `SpecTable` comparison render, `CompatBadge` color mapping (green/red/amber), catalog-panel filtering, and the refusal rendering. One Playwright smoke test: click an example prompt → product cards appear.

## CI (GitHub Actions)

`ci.yml`: lint (Ruff + Black + mypy for Python, ESLint + tsc for frontend), run backend and frontend tests, and `docker compose build`. The eval job is a **separate, manually-triggered** workflow that requires an API-key secret so the default CI stays free and offline.

## README (make it portfolio-grade)

Include: one-line pitch; an animated GIF/screenshot of a rider-profile question producing product cards + a comparison table + compat badges; a **Mermaid** diagram of the constrained-agent + tool-calling + grounding pipeline; a **"how the domain constraint works"** section (system prompt + code-level grounding guardrail + refusal backstop); the eval results table (correctness / grounding / refusal rate); one-command quickstart; the tech-stack rationale; and a **prominent, unmissable note that all product data is synthetic, brands/models are fictional, and specs are illustrative mock data — not real product specifications.** Add badges (CI, license). MIT license.

## Out of scope (explicit non-goals)

<!-- ASSUMED: non-goals inferred from the brief's demo/portfolio intent; adjust if any should move in-scope. -->

- **Real product data** — no scraping, no real brands, no live pricing or inventory. All data stays synthetic.
- **Commerce** — no cart, checkout, payments, or order flow. "Build my setup" recommends; it does not sell.
- **User accounts / auth / persistence of chat history** — sessions are ephemeral; `history` is passed per-request by the client.
- **RAG over unstructured documents** — the agent queries structured DB rows only (the embedding fuzzy-search stretch goal is the sole, env-flagged exception).
- **Multi-tenancy, rate limiting, production hardening** — this is a single-user demo; note it in the README, don't build it.
- **Mobile app / i18n / unit localization** — web only, English only (metric/imperial toggle is a stretch goal, not core).
- **Model fine-tuning** — behavior comes from prompting + tools + code guardrails, deliberately.

## Known risks & constraints

- **Grounding validator precision.** Matching "every number in the answer to a tool result" is heuristic — unit conversions (kg↔lbs), rounding ("about 150 L"), and derived arithmetic can cause false positives that strip legitimate content. Mitigation: normalize units before matching, allow tolerance on rounded values, and cover these cases in the eval set. This validator is the project's core claim — its edge cases are the main technical risk.
- **Provider variance in function calling.** The OpenAI-compatible abstraction hides real differences in tool-call reliability, especially on local models (Ollama/vLLM). Evals must be re-run and reported per model; a model that can't tool-call reliably degrades the whole demo.
- **Refusal backstop can misfire.** A lightweight domain classifier will have edge cases (e.g., "what's the water temperature for paddling?"). Prefer false-refusals over off-topic answers, and measure the rate in evals.
- **Eval cost / CI constraint.** Live-model evals need an API key and money — hence the separate, manually-triggered eval workflow; default CI must stay offline with a mocked model.
- **SQLite concurrency** is fine for a single-user demo but is a stated constraint, not an oversight — the SQLAlchemy layer keeps a Postgres swap small.
- **Legal constraint (hard):** fictional brands/models only, and the mock-data disclaimer must be visible in both UI and README. Presenting invented specs as real products is the one unrecoverable failure mode for a public portfolio repo.

## Definition of done (acceptance criteria)

- [ ] `docker compose up` serves the UI on `:3006` and the API on `:8006`; the catalog is seeded; at least three example prompts return grounded product cards and/or a comparison table.
- [ ] Every spec in an answer traces to a tool result; the **no-ungrounded-spec** test passes and the agent says **"I don't have that spec"** when the DB lacks it.
- [ ] Off-topic questions are **refused** with zero tools run; the refusal test passes.
- [ ] Every `/api/chat` response returns the typed `ChatResponse`, and the UI renders cards / tables / compat badges from the structured payload — **never** raw model text.
- [ ] `check_compatibility` correctly passes and fails the seeded compatible/incompatible pairings; badges color-map correctly.
- [ ] `make eval` runs the harness and prints a correctness / grounding / refusal table.
- [ ] CI is green; README renders with a working demo GIF and Mermaid diagram; the mock-data disclaimer is visible in **both** the UI and the README.

## Stretch goals (only after the above)

A dedicated **side-by-side comparison builder** (pick N boards from the catalog); an **"explain this recommendation"** trace showing which tool rows drove each pick; **save/share a setup** as a read-only link; a **metric/imperial unit toggle**; light **fuzzy search** (embedding lookup over `best_for` descriptions) behind an env flag for "vibey" queries like "something chill for sunset paddles"; a compatibility **fit-check widget** in the catalog panel independent of chat.

---

### Assumptions I made (edit freely)
- **All brands, models, and specs are fictional and mock** — chosen deliberately to avoid trademark issues and to never present invented numbers as a real product's specifications. Everything is labeled illustrative in the UI and README.
- **SQLite seeded from JSON** for zero-config portability and a clone-and-run demo; swap in Postgres if your portfolio leans that way — the SQLAlchemy layer makes it a small change.
- **Product images are placeholders** (solid-color / blurred SVGs generated from the board type); wire in real assets locally if you want.
- Provider-agnostic LLM config assumes an **OpenAI-compatible, function-calling-capable** endpoint; point `LLM_*` at OpenAI, a compatible gateway, or a local model.
- The **compatibility rules are a simplified, illustrative fitment model** (fin-box match, pump PSI/valve, leash-by-use, paddle-by-height), not a real-world gear-compatibility database.
