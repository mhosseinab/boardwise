# BoardWise API image (S20).
#
# Multi-stage build: the `builder` stage compiles/install dependencies into a
# venv; the `final` stage is python:3.11-slim with only the venv + source, run
# as a non-root user (spec §Infrastructure).
#
# `app.db.seed` resolves `sample_data/` via `Path(__file__).resolve().parents[3]`
# (repo-root-relative, load-bearing — see backend/app/db/seed.py). To keep that
# resolution correct in the image we install the package *editable*
# (`pip install -e .`) so `__file__` keeps pointing at the source tree we COPY
# in below, and we preserve the same repo layout: `/app/backend/app/...` with
# `/app/sample_data/` as its sibling. A non-editable install would copy the
# package into site-packages and break that path.

FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/ ./backend/

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e ./backend

FROM python:3.11-slim AS final

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system boardwise \
    && useradd --system --gid boardwise --home-dir /app --shell /usr/sbin/nologin boardwise

COPY --from=builder /opt/venv /opt/venv
COPY backend/ ./backend/
COPY sample_data/ ./sample_data/

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

RUN chown -R boardwise:boardwise /app

USER boardwise
WORKDIR /app/backend

EXPOSE 8006

HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=10 \
    CMD curl -f http://localhost:8006/api/health || exit 1

# Single worker: the app seeds SQLite from its lifespan startup hook, and that
# seed is idempotent-by-row-check, not by transaction lock — concurrent
# workers racing the same empty DB on first boot could double-insert. SQLite's
# single-writer model plus this being a single-user demo (spec §Known risks)
# make one worker the sensible count here, not a resource compromise.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8006", "--workers", "1"]
