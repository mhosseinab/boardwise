#!/usr/bin/env bash
# Greps tracked files (outside docs/) for real SUP brand names.
# BoardWise's catalog must only ever contain fictional brands
# (Aquara, Riptide, Zephyr, Cascade, Velocity, Fjord — plan §4.1).
# Extend REAL_BRANDS as more real-world names are identified.
set -euo pipefail

REAL_BRANDS=(
  "Bluefin"
  "Aqua Marina"
  "Hala"
  "SIC"
  "Tower"
  "Isle"
  "Red Paddle"
  "BOTE"
  "iRocker"
  "NIXY"
  "Retrospec"
  "Atoll"
  "Thurso Surf"
  "Gili Sports"
)

cd "$(git rev-parse --show-toplevel)"

pattern=$(IFS='|'; echo "${REAL_BRANDS[*]}")

git ls-files \
  | grep -v '^docs/' \
  | xargs -I{} grep -HniE "$pattern" {} 2>/dev/null || true
