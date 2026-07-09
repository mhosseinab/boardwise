"""Grounding validator (S9) and refusal backstop (S10 — added later, same module).

RULE (project rule #2): the grounding invariant is enforced **in code**, never only in
the system prompt. `validate_grounding` is a PURE function — no LLM call, no DB access,
no network I/O, no wall-clock or randomness. It takes the agent's free-text answer plus
that turn's tool results and returns a `GroundingResult` with every ungrounded
spec/number removed.

## Method

1. **Claim extraction.** Scan the answer text with unit-anchored regexes for numbers
   that carry a recognized spec unit: `kg`, `lbs`/`lb`, `psi`, `ft`, `in`, feet+inches
   (`12'0"`), `L` (liters), `$` (price), `%`. Spelled-out and plural-no-space unit
   words are recognized too (`kilogram(s)`/`kgs`, `pound(s)`, `liter(s)`/`litre(s)`,
   `dollar(s)`, `feet`/`foot`, `inch(es)`, `percent`) so a claim phrased as "999
   kilograms", "999kgs", "12 feet", "3.5 inches", "50 percent", or "150 litres" is
   extracted exactly like its abbreviated form. A bare number with no recognized unit
   (e.g. "2 boards",
   an ordinal, a rider's age) is never extracted as a claim and is therefore never
   touched — this is the allowlist for counts that are not product specs.

2. **Grounded-value pool.** `tool_results` (a list of dicts — raw tool-call return
   values, already JSON-ish) is walked recursively (including nested dicts/lists, e.g.
   a `recommend_setup` bundle) to collect every numeric leaf (`int`/`float`, excluding
   `bool`) into a flat pool, and every string leaf into a separate pool used for the
   entity-name allowlist (below). The pool is flat across fields by design (v1
   heuristic, documented risk): it does not know which DB column a number belongs to,
   only that it was returned by a tool this turn.

3. **Matching.**
   - **Exact-match categories — `psi`, `$` (price), `%`.** No unit conversion, no
     rounding tolerance (beyond float epsilon). Spec/PSI/price claims must equal a
     pooled number exactly, because these are the numbers a purchase decision hinges
     on and a false-pass here is the project's core risk.
   - **Tolerance categories — `kg`/`lbs` (weight), `ft`/feet-inches (length), `L`
     (volume).** Tolerance = `max(0.5, 2% of the claimed value)`, absolute difference,
     to accommodate rounded phrasing ("about 150 L" against a stored 149.6). `in`
     (bare inches, e.g. board width/thickness) is matched directly against the pool
     with the same tolerance and no conversion, because those spec fields are already
     stored in inches.
   - **Unit conversion.** `kg <-> lbs` (factor 2.20462) and feet-inches -> decimal
     feet are applied when comparing a weight or length claim against the pool, per
     SPEC's grounding guardrail requirement. **`ft <-> cm` is not wired to an
     extractor** in v1 (no `cm` unit is recognized in claim text), so that conversion
     path is currently inert; it is left in the matcher as a documented placeholder
     rather than removed, since board length specs are always quoted in feet in this
     catalog. If a `cm` claim format is ever added to the extractor, the conversion is
     already implemented on the matching side.
   - **Derived sums.** v1 does **not** attempt subset-sum / arithmetic reconstruction
     (e.g. verifying "$450 board + $80 paddle = $530 total" by summing pool values). A
     derived total is considered grounded only if that literal total number was itself
     present in a tool result (which it will be whenever a tool computes and returns a
     bundle total). Implementing subset-sum matching would let a hallucinated total
     slip through as long as its parts happen to sum correctly by coincidence, which
     undermines the anti-hallucination guarantee — so it is deliberately out of scope.

4. **Entity-name allowlist.** Before a claim is checked for groundedness, its text span
   is checked against every occurrence, in the answer, of a string leaf from
   `tool_results` that contains a digit (e.g. a model name like `"Atlas 12'0\""`). If
   the claim's span falls inside such an occurrence, it is skipped entirely — it is
   part of a grounded entity's name, not a spec assertion, and must never be stripped.

5. **Strip policy (documented, simple).** When a claim fails to ground, the **entire
   sentence** containing it is replaced with the fixed disclaimer `"I don't have that
   spec in my catalog."` — never a partial in-place number swap, which risks producing
   grammatically broken or misleading half-edited prose. Sentence boundaries are the
   regions between `. `/`! `/`? ` delimiters. A sentence is replaced at most once even
   if it contains multiple ungrounded claims. All untouched sentences (and the
   whitespace between them) are preserved byte-for-byte via right-to-left,
   offset-based splicing — no answer is ever rebuilt by re-joining tokens.

`grounded` is `True` iff nothing had to be stripped.

## Refusal backstop (S10)

RULE (project rule #4 / SPEC "Known risks" — "Refusal backstop can misfire"): domain
refusal is **prompt-driven and backstopped by a deterministic classifier**, per SPEC
"Backend requirements" item 4 and decision §4.10 in the plan doc. `is_in_domain` is a
PURE function — no embeddings, no LLM/model call, no DB, no I/O — a heuristic combining
SUP/gear vocabulary with question-shape patterns. **POLICY: when uncertain, return
`False`** (prefer a false-refusal over letting an off-topic answer through) — this is
the documented, accepted trade-off from the plan's risk R3.

The in-domain gate is a set of **strong keywords** (`paddleboard`, `sup`, `fin`,
`paddle`, `pump`, `leash`, `psi`, `board`/`boards`, board-type words like
`whitewater`, `fin box`/`fin-box`, `valve`, and the fictional brand names
`Aquara`/`Riptide`/`Zephyr`/`Cascade`/`Velocity`/`Fjord`) that are unambiguous enough
in this domain to classify a message in-domain on their own — deliberately narrower
than a second "question-shape" tier that was drafted and then rejected: gating
generic terms ("capacity", "volume", "length", "setup", "recommend"...) on generic
interrogative shape ("what is...?", "how...?") does not disambiguate *topic*, only
sentence form — an off-topic question is still a question, so e.g. "what's the
volume of a sphere?" would classify in-domain purely on "volume" + "what's...?".
That is exactly the false-negative-on-refusal failure mode the POLICY forbids, so
the design keeps a single, narrow, unambiguous-keyword gate instead (see
`test_refusal.py`'s regression tests pinning generic weak-word-plus-question-shape
messages to `False`).

A separate jailbreak-pattern check (e.g. "ignore your instructions", "act as a...",
"system prompt") short-circuits straight to `False` regardless of vocabulary, so a
prompt-injection attempt can't ride a domain keyword into a bypass — this is the
literal SPEC requirement ("a jailbreak can't drag it off-topic").

`build_refusal()` returns the fixed, friendly redirect text used whenever
`is_in_domain` (or the agent's own prompt-driven refusal) determines the turn is out
of scope. Per SPEC item 4, a refusal runs **zero tools**.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_LB_PER_KG = 2.20462
_CM_PER_FT = 30.48

_DISCLAIMER = "I don't have that spec in my catalog."

# Ordered so the feet-inches combo (`12'0"`) is tried before the bare `ft`/`in`
# patterns; in practice no ambiguity exists because each alternative requires a
# distinct literal unit suffix that can only match one way at a given position.
_CLAIM_PATTERN = re.compile(
    r"""
    (?P<ftin>\d+)'(?P<ftin_in>\d{1,2})"          # 12'0"
    | \$(?P<price>\d+(?:,\d{3})*(?:\.\d+)?)  # $899 / $1,299.50 / $5000
    | (?P<price_word>\d+(?:,\d{3})*(?:\.\d+)?)\s?dollars?\b  # 5000 dollars
    | (?P<psi>\d+(?:\.\d+)?)\s?psi\b
    | (?P<kg>\d+(?:\.\d+)?)\s?(?:kgs?|kilograms?)\b
    | (?P<lbs>\d+(?:\.\d+)?)\s?(?:lbs?|pounds?)\b
    | (?P<ft>\d+(?:\.\d+)?)\s?(?:ft|feet|foot)\b
    | (?P<inch>\d+(?:\.\d+)?)\s?(?:in|inch(?:es)?)\b
    | (?P<liter>\d+(?:\.\d+)?)\s?(?:[lL]|liters?|litres?)\b
    | (?P<percent>\d+(?:\.\d+)?)\s?(?:%|percent\b)
    """,
    re.VERBOSE | re.IGNORECASE,
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

_EXACT_UNITS = {"price", "psi", "percent"}


@dataclass(frozen=True)
class GroundingResult:
    """Outcome of `validate_grounding`."""

    clean_answer: str
    stripped_claims: list[str] = field(default_factory=list)
    grounded: bool = True


@dataclass(frozen=True)
class _Claim:
    unit: str
    value: float
    start: int
    end: int
    raw_text: str


def _collect_pools(tool_results: list[dict]) -> tuple[set[float], list[str]]:
    """Recursively walk `tool_results`, returning (numeric pool, string pool)."""
    numbers: set[float] = set()
    strings: list[str] = []

    def _walk(obj: object) -> None:
        if isinstance(obj, bool):
            return
        if isinstance(obj, (int, float)):
            numbers.add(float(obj))
        elif isinstance(obj, str):
            strings.append(obj)
        elif isinstance(obj, dict):
            for value in obj.values():
                _walk(value)
        elif isinstance(obj, (list, tuple, set)):
            for value in obj:
                _walk(value)

    for item in tool_results:
        _walk(item)
    return numbers, strings


def _allowlisted_spans(answer: str, string_pool: list[str]) -> list[tuple[int, int]]:
    """Spans in `answer` inside a grounded entity name that contains a digit."""
    spans: list[tuple[int, int]] = []
    for text in string_pool:
        if not text or not any(ch.isdigit() for ch in text):
            continue
        start = 0
        while True:
            idx = answer.find(text, start)
            if idx == -1:
                break
            spans.append((idx, idx + len(text)))
            start = idx + 1
    return spans


def _in_allowlist(
    span: tuple[int, int], allowlist_spans: list[tuple[int, int]]
) -> bool:
    start, end = span
    return any(a_start <= start and end <= a_end for a_start, a_end in allowlist_spans)


def _extract_claims(
    answer: str, allowlist_spans: list[tuple[int, int]]
) -> list[_Claim]:
    claims: list[_Claim] = []
    for match in _CLAIM_PATTERN.finditer(answer):
        span = match.span()
        if _in_allowlist(span, allowlist_spans):
            continue
        groups = match.groupdict()
        raw = match.group(0)
        if groups["ftin"] is not None:
            feet = float(groups["ftin"])
            inches = float(groups["ftin_in"])
            claims.append(_Claim("ftin", feet + inches / 12.0, *span, raw))
        elif groups["price"] is not None:
            value = float(groups["price"].replace(",", ""))
            claims.append(_Claim("price", value, *span, raw))
        elif groups["price_word"] is not None:
            value = float(groups["price_word"].replace(",", ""))
            claims.append(_Claim("price", value, *span, raw))
        elif groups["psi"] is not None:
            claims.append(_Claim("psi", float(groups["psi"]), *span, raw))
        elif groups["kg"] is not None:
            claims.append(_Claim("kg", float(groups["kg"]), *span, raw))
        elif groups["lbs"] is not None:
            claims.append(_Claim("lbs", float(groups["lbs"]), *span, raw))
        elif groups["ft"] is not None:
            claims.append(_Claim("ft", float(groups["ft"]), *span, raw))
        elif groups["inch"] is not None:
            claims.append(_Claim("inch", float(groups["inch"]), *span, raw))
        elif groups["liter"] is not None:
            claims.append(_Claim("liter", float(groups["liter"]), *span, raw))
        elif groups["percent"] is not None:
            claims.append(_Claim("percent", float(groups["percent"]), *span, raw))
    return claims


def _is_grounded(claim: _Claim, numeric_pool: set[float]) -> bool:
    if not numeric_pool:
        return False

    if claim.unit in _EXACT_UNITS:
        tol = 1e-6
        return any(abs(claim.value - pooled) <= tol for pooled in numeric_pool)

    tol = max(0.5, abs(claim.value) * 0.02)

    if claim.unit in ("kg", "lbs"):
        candidates = numeric_pool | {p * _LB_PER_KG for p in numeric_pool}
    elif claim.unit in ("ft", "ftin"):
        candidates = numeric_pool | {p / _CM_PER_FT for p in numeric_pool}
    else:  # inch, liter
        candidates = numeric_pool

    return any(abs(claim.value - candidate) <= tol for candidate in candidates)


def _sentence_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    offset = 0
    for part in _SENTENCE_SPLIT.split(text):
        if part == "":
            continue
        start = text.index(part, offset)
        end = start + len(part)
        spans.append((start, end))
        offset = end
    return spans


def validate_grounding(answer: str, tool_results: list[dict]) -> GroundingResult:
    """Strip every spec/number in `answer` absent from the union of `tool_results`.

    Pure function: no LLM, no DB, no I/O. See the module docstring for the matching
    and strip policy.
    """
    numeric_pool, string_pool = _collect_pools(tool_results)
    allowlist_spans = _allowlisted_spans(answer, string_pool)
    claims = _extract_claims(answer, allowlist_spans)

    ungrounded = [c for c in claims if not _is_grounded(c, numeric_pool)]
    if not ungrounded:
        return GroundingResult(clean_answer=answer, stripped_claims=[], grounded=True)

    sentence_spans = _sentence_spans(answer)
    marked: set[tuple[int, int]] = set()
    for claim in ungrounded:
        for sent_start, sent_end in sentence_spans:
            if sent_start <= claim.start and claim.end <= sent_end:
                marked.add((sent_start, sent_end))
                break

    clean_answer = answer
    for sent_start, sent_end in sorted(marked, reverse=True):
        clean_answer = clean_answer[:sent_start] + _DISCLAIMER + clean_answer[sent_end:]

    stripped_claims = list(dict.fromkeys(c.raw_text for c in ungrounded))
    return GroundingResult(
        clean_answer=clean_answer, stripped_claims=stripped_claims, grounded=False
    )


# ---------------------------------------------------------------------------
# Refusal backstop (S10) — see module docstring "Refusal backstop" section.
# ---------------------------------------------------------------------------

_JAILBREAK_PATTERN = re.compile(
    r"""
    ignore\s+(?:your|all|any|previous|prior)?\s*instructions
    | disregard\s+(?:your|all|any|previous|prior)?\s*(?:instructions|the\s+above)
    | forget\s+(?:your|all|any|previous|prior)?\s*instructions
    | you\s+are\s+now\b
    | pretend\s+(?:you\s+are|to\s+be)\b
    | act\s+as\s+(?:a|an)\b
    | system\s+prompt
    | jailbreak
    | reveal\s+your\s+(?:prompt|instructions|system)
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Unambiguous in this domain — a single hit is enough to classify in-domain. See
# the module docstring for why this stays a single narrow tier rather than adding
# a second, generic-word-plus-question-shape tier.
_DOMAIN_KEYWORDS = re.compile(
    r"""
    \b(
        paddleboards?
        | sup
        | fins?
        | paddles?
        | pumps?
        | leash(?:es)?
        | psi
        | boards?
        | whitewater
        | valve
        | aquara | riptide | zephyr | cascade | velocity | fjord
    )\b
    | fin[- ]?box
    """,
    re.VERBOSE | re.IGNORECASE,
)

_REFUSAL_TEXT = (
    "I'm your paddleboard gear assistant, so I can't help with that one. "
    "I'd love to help you find the right board, fin, paddle, pump, or leash "
    "instead — ask me anything about SUP gear!"
)


def is_in_domain(message: str) -> bool:
    """Deterministic heuristic: is `message` in-domain (SUP/paddleboard gear)?

    Pure function: no embeddings, no model call, no I/O. POLICY: uncertain cases
    return `False` (prefer a false-refusal over an off-topic answer — see module
    docstring). A jailbreak-shaped message is refused regardless of vocabulary.
    """
    text = message.strip()
    if not text:
        return False
    if _JAILBREAK_PATTERN.search(text):
        return False
    return bool(_DOMAIN_KEYWORDS.search(text))


def build_refusal() -> str:
    """The fixed, friendly redirect text for an out-of-domain / refused turn."""
    return _REFUSAL_TEXT
