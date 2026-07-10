"""Structured request logs + in-process metrics for `/api/chat` (S13, SPEC
"Backend requirements" item 6): one structured JSON log line per request and
an in-memory registry backing `GET /api/metrics`.

Scope: this module only records what `main.chat()` can observe around the
frozen S12 pipeline call — wall-clock latency, the tool names on the
returned `ChatResponse.tools_used`, and `.refused`/`.prompt_version`.
`run_agent`/`handle_chat` are out of this step's edit list and currently
surface no model token-usage metadata, so `token_counts`/`estimated_cost_usd`
are recorded only when a caller explicitly supplies them and are `null`
otherwise — never fabricated.

In-memory only (rule: no external metrics deps) — correct for this
single-user demo; state resets on process restart. A single process-global
`metrics_registry` backs `GET /api/metrics`; `reset()` exists purely for
test isolation.
"""

import json
import logging
import math
import uuid
from dataclasses import dataclass
from threading import Lock
from typing import Any

logger = logging.getLogger("boardwise.observability")
logger.setLevel(logging.INFO)
if not logger.handlers:
    # Own handler so the JSON line is actually emitted (stdout) regardless
    # of the ambient root/uvicorn logging config, which by default doesn't
    # attach a handler to root and leaves this logger's effective level at
    # WARNING. `propagate` is left at its default (True) so pytest's
    # `caplog`, which captures via a handler on the root logger, still sees
    # every record.
    _stream_handler = logging.StreamHandler()
    _stream_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_stream_handler)


@dataclass
class ChatRequestRecord:
    """One `/api/chat` turn's observability facts: enough to produce one
    structured JSON log line and one metrics-registry update."""

    request_id: str
    latency_ms: int
    tool_names: list[str]
    refused: bool
    prompt_version: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    estimated_cost_usd: float | None = None

    def token_counts(self) -> dict[str, int] | None:
        if self.prompt_tokens is None and self.completion_tokens is None:
            return None
        return {
            "prompt_tokens": self.prompt_tokens or 0,
            "completion_tokens": self.completion_tokens or 0,
        }

    def log_line(self) -> str:
        payload = {
            "request_id": self.request_id,
            "latency_ms": self.latency_ms,
            "tools": self.tool_names,
            "token_counts": self.token_counts(),
            "estimated_cost_usd": self.estimated_cost_usd,
            "refused": self.refused,
            "prompt_version": self.prompt_version,
        }
        return json.dumps(payload, sort_keys=True)


def _percentile(sorted_values: list[int], pct: float) -> float:
    """Linear-interpolation percentile over an already-sorted sample."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    rank = (pct / 100) * (len(sorted_values) - 1)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return float(sorted_values[int(rank)])
    lower_value = sorted_values[lower]
    upper_value = sorted_values[upper]
    fraction = rank - lower
    return lower_value + (upper_value - lower_value) * fraction


class MetricsRegistry:
    """In-process request-count / latency-reservoir / refusal-count /
    tools-per-turn accumulator (rule: in-memory is correct for this
    single-user demo — no external metrics deps)."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._latencies_ms: list[int] = []
        self._refusals = 0
        self._tool_counts: list[int] = []

    def record(self, record: ChatRequestRecord) -> None:
        with self._lock:
            self._latencies_ms.append(record.latency_ms)
            if record.refused:
                self._refusals += 1
            self._tool_counts.append(len(record.tool_names))

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            latencies = sorted(self._latencies_ms)
            requests = len(latencies)
            refusals = self._refusals
            tool_counts = list(self._tool_counts)

        return {
            "requests": requests,
            "p50_ms": _percentile(latencies, 50),
            "p95_ms": _percentile(latencies, 95),
            "refusal_rate": (refusals / requests) if requests else 0.0,
            "avg_tools_per_turn": (
                sum(tool_counts) / len(tool_counts) if tool_counts else 0.0
            ),
        }

    def reset(self) -> None:
        """Clear all recorded requests. Test isolation only — the running
        app never calls this."""
        with self._lock:
            self._latencies_ms.clear()
            self._refusals = 0
            self._tool_counts.clear()


metrics_registry = MetricsRegistry()


def new_request_id() -> str:
    return uuid.uuid4().hex


def record_chat_request(
    *,
    request_id: str,
    latency_ms: int,
    tool_names: list[str],
    refused: bool,
    prompt_version: str,
) -> ChatRequestRecord:
    """Build one `ChatRequestRecord`, emit it as one structured JSON log
    line, and fold it into the process-global `metrics_registry`. Returns
    the record so callers/tests can inspect the facts without re-parsing
    the log line."""
    record = ChatRequestRecord(
        request_id=request_id,
        latency_ms=latency_ms,
        tool_names=tool_names,
        refused=refused,
        prompt_version=prompt_version,
    )
    logger.info(record.log_line())
    metrics_registry.record(record)
    return record
