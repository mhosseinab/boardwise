"""Offline eval harness for BoardWise (S19 — SPEC "AI-engineering rigor").

Loads the labeled cases in `cases.yaml` and drives the real `/api/chat`
pipeline (`app.agent.pipeline.handle_chat`) in-process for each one, scoring:

  (a) correctness   — the stated board ids / compatibility verdicts / spec
                       numbers match the seeded DB ground truth in each
                       case's `expect` block.
  (b) grounding      — no spec appears in the answer that isn't present in
                        that turn's tool results (the anti-hallucination
                        guarantee `guardrails.validate_grounding` enforces).
  (c) refusal        — off-topic cases are refused with zero tool calls.

`--mode offline` (default) replays each case's canned tool-call transcript
through a fake chat model — the same duck-typed `bind_tools(tools).invoke`
seam `backend/tests/test_chat_signature.py` uses (decision §4.9) — so this
script makes no network call and needs no `LLM_API_KEY`. `--mode live` passes
`model=None` through to `handle_chat`, which makes `run_agent` build the
env-configured model itself (`app.agent.agent.build_default_model`); that
path exists for the S24 gate and is never exercised by this step or by
default CI.

Prints a table of (category, cases, pass, rate), plus avg tools/turn and
tool-error rate, and logs the model name + `prompt_version` every response
was stamped with. Exits non-zero if any category's pass rate is below 1.0.
"""

import argparse
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from langchain_core.messages import AIMessage

_EVALS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _EVALS_DIR.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
# Insert this checkout's own backend onto sys.path (rather than relying on
# whatever `boardwise-backend` happens to be pip-installed as elsewhere) so
# the harness always exercises this worktree's grounding/refusal code.
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.agent.pipeline import handle_chat  # noqa: E402
from app.db.seed import seed  # noqa: E402
from app.db.session import session_scope  # noqa: E402
from app.schemas import ChatRequest, ChatResponse  # noqa: E402

_CASES_PATH = _EVALS_DIR / "cases.yaml"
_OFFLINE_MODEL_NAME = "fake-offline-v1"
_CATEGORIES = ("correctness", "grounding", "refusal")


# --- fake model seam (offline mode) -----------------------------------------


class _FakeBoundModel:
    """Stand-in for `chat_model.bind_tools(tools)` — replays one `AIMessage`
    per `.invoke()` call (same shape as `test_chat_signature.py`'s fake).
    """

    def __init__(self, responses: list[AIMessage]) -> None:
        self._responses = responses
        self.invoke_count = 0

    def invoke(self, _messages: list[Any]) -> AIMessage:
        response = self._responses[min(self.invoke_count, len(self._responses) - 1)]
        self.invoke_count += 1
        return response


class _FakeChatModel:
    """Stand-in for `ChatOpenAI`: exposes only `bind_tools(tools)`, exactly
    the surface `run_agent` relies on (decision §4.9).
    """

    def __init__(self, responses: list[AIMessage]) -> None:
        self._responses = responses

    def bind_tools(self, _tools: list[Any]) -> _FakeBoundModel:
        return _FakeBoundModel(self._responses)


class _AssertNeverInvokedModel:
    """A model that raises if it is ever touched — refusal-category cases use
    this to prove the turn never reaches `run_agent`/the model at all, not
    merely that the eventual answer happens to carry no tool calls.
    """

    def bind_tools(self, _tools: list[Any]) -> Any:
        raise AssertionError("model must never be invoked on a refused turn")


def _build_transcript(turns: list[dict[str, Any]]) -> list[AIMessage]:
    """Turn a case's YAML `transcript` into the `AIMessage` list a
    `_FakeChatModel` replays, one entry per model round-trip. Tool-call ids
    are assigned sequentially by the harness (the YAML only names `name`/
    `args`).
    """
    messages: list[AIMessage] = []
    call_id = 0
    for turn in turns:
        tool_calls = []
        for call in turn.get("tool_calls") or []:
            call_id += 1
            tool_calls.append(
                {
                    "name": call["name"],
                    "args": call.get("args") or {},
                    "id": f"call_{call_id}",
                }
            )
        messages.append(
            AIMessage(content=turn.get("content", ""), tool_calls=tool_calls)
        )
    return messages


# --- case loading -------------------------------------------------------


@dataclass
class EvalCase:
    id: str
    category: str
    prompt: str
    transcript: list[dict[str, Any]]
    expect: dict[str, Any]


def _load_cases(path: Path) -> list[EvalCase]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [
        EvalCase(
            id=raw["id"],
            category=raw["category"],
            prompt=raw["prompt"],
            transcript=raw.get("transcript") or [],
            expect=raw.get("expect") or {},
        )
        for raw in data["cases"]
    ]


# --- DB fixture -----------------------------------------------------------


def _seed_tmp_db() -> str:
    """Seed a fresh, isolated tmp SQLite DB from `sample_data/*.json` and
    return its URL. The agent's tool wrappers always read `DATABASE_URL`
    from the environment (they take no explicit override), so the caller
    must set `os.environ["DATABASE_URL"]` to this before running any case.
    """
    tmp_dir = tempfile.mkdtemp(prefix="boardwise-eval-")
    db_url = f"sqlite:///{Path(tmp_dir) / 'eval.sqlite3'}"
    with session_scope(db_url) as session:
        seed(session)
    return db_url


# --- scoring ----------------------------------------------------------------


@dataclass
class CaseResult:
    case: EvalCase
    response: ChatResponse
    checks: list[tuple[str, bool]]
    passed: bool
    tool_error_count: int


def _check_board_ids(response: ChatResponse, expected: list[str]) -> bool:
    return {card.id for card in response.cards} == set(expected)


def _check_compatibility(
    response: ChatResponse, expected: list[dict[str, Any]]
) -> bool:
    return all(
        any(
            cr.board_id == entry["board_id"]
            and cr.accessory_id == entry["accessory_id"]
            and cr.compatible == entry["compatible"]
            for cr in response.compatibility
        )
        for entry in expected
    )


def _score_case(case: EvalCase, response: ChatResponse) -> CaseResult:
    expect = case.expect
    checks: list[tuple[str, bool]] = [
        ("refused", response.refused == expect.get("refused", False))
    ]
    if "board_ids" in expect:
        checks.append(("board_ids", _check_board_ids(response, expect["board_ids"])))
    if "compatibility" in expect:
        checks.append(
            ("compatibility", _check_compatibility(response, expect["compatibility"]))
        )
    if "answer_contains" in expect:
        checks.append(
            (
                "answer_contains",
                all(s in response.answer for s in expect["answer_contains"]),
            )
        )
    if "answer_not_contains" in expect:
        checks.append(
            (
                "answer_not_contains",
                all(s not in response.answer for s in expect["answer_not_contains"]),
            )
        )
    if "tools_used_count" in expect:
        checks.append(
            (
                "tools_used_count",
                len(response.tools_used) == expect["tools_used_count"],
            )
        )

    tool_error_count = sum(
        1 for call in response.tools_used if '"error"' in call.result_summary
    )
    passed = all(ok for _name, ok in checks)
    return CaseResult(
        case=case,
        response=response,
        checks=checks,
        passed=passed,
        tool_error_count=tool_error_count,
    )


def _offline_model(case: EvalCase) -> Any:
    if case.category == "refusal" and not case.transcript:
        return _AssertNeverInvokedModel()
    return _FakeChatModel(_build_transcript(case.transcript))


def _run_case(case: EvalCase, mode: str) -> ChatResponse:
    # `mode == "live"` passes `model=None` through so `run_agent` builds the
    # env-configured model itself (S24 gate) — never exercised here.
    model = _offline_model(case) if mode == "offline" else None
    return handle_chat(ChatRequest(message=case.prompt), model=model)


# --- reporting ----------------------------------------------------------


def _print_report(
    results: list[CaseResult], model_name: str, prompt_version: str
) -> bool:
    print(f"model: {model_name}")
    print(f"prompt_version: {prompt_version}")
    print()

    header = f"{'category':<12}{'cases':>7}{'pass':>7}{'rate':>7}"
    print(header)
    print("-" * len(header))

    overall_ok = True
    for category in _CATEGORIES:
        subset = [r for r in results if r.case.category == category]
        cases_n = len(subset)
        pass_n = sum(1 for r in subset if r.passed)
        rate = pass_n / cases_n if cases_n else 0.0
        overall_ok = overall_ok and rate >= 1.0
        print(f"{category:<12}{cases_n:>7}{pass_n:>7}{rate:>7.2f}")

    total_tool_calls = sum(len(r.response.tools_used) for r in results)
    total_cases = len(results)
    avg_tools_per_turn = total_tool_calls / total_cases if total_cases else 0.0
    tool_errors = sum(r.tool_error_count for r in results)
    tool_error_rate = tool_errors / total_tool_calls if total_tool_calls else 0.0

    print()
    print(f"avg tools/turn: {avg_tools_per_turn:.2f}")
    print(f"tool-error rate: {tool_error_rate:.2f}")

    failed = [r.case.id for r in results if not r.passed]
    if failed:
        print()
        print(f"FAILED cases: {', '.join(failed)}")

    return overall_ok


# --- entrypoint -----------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BoardWise eval harness (S19).")
    parser.add_argument(
        "--mode",
        choices=["offline", "live"],
        default="offline",
        help=(
            "offline (default) replays canned per-case transcripts through a "
            "fake model, no network call. live builds the env-configured "
            "model instead (S24 gate — do not run from CI or a step worker)."
        ),
    )
    parser.add_argument("--cases", type=Path, default=_CASES_PATH)
    args = parser.parse_args(argv)

    cases = _load_cases(args.cases)

    db_url = _seed_tmp_db()
    os.environ["DATABASE_URL"] = db_url

    results = []
    prompt_version = ""
    for case in cases:
        response = _run_case(case, args.mode)
        prompt_version = response.prompt_version
        results.append(_score_case(case, response))

    model_name = (
        _OFFLINE_MODEL_NAME
        if args.mode == "offline"
        else os.environ.get("LLM_MODEL", "<unset>")
    )
    overall_ok = _print_report(results, model_name, prompt_version)

    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
