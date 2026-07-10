#!/usr/bin/env bash
# Checks for likely secrets in tracked files and confirms .env hygiene.
# BoardWise requires LLM_API_KEY (and any other secret) to be env-only,
# never committed, never hardcoded in source or fixtures (plan §9).
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "--- likely secret patterns in tracked files ---"
git ls-files -z \
  | xargs -0 grep -HnE \
    "sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|api[_-]?key['\"]?\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]" \
    2>/dev/null | grep -v '\.env\.example' || true

echo "--- .env tracked-by-git check ---"
if git ls-files --error-unmatch .env >/dev/null 2>&1; then
  echo ".env IS TRACKED BY GIT — must be removed and rotated any keys it held"
fi

echo "--- .gitignore coverage check ---"
if [ -f .gitignore ] && grep -qxF '.env' .gitignore; then
  echo ".env is gitignored: OK"
else
  echo ".env is NOT listed in .gitignore"
fi
