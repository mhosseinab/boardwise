"""Loader for versioned prompt assets.

Prompts are files, not inline strings — no other module may embed prompt text
(rule: prompts are assets). Each prompt file's name carries its version as a
trailing `_v<N>` suffix (e.g. `system_v1.md`); `load_prompt` reads the file and
derives `prompt_version` from that suffix so callers can stamp responses with
the version that actually produced them.
"""

import re
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent
_VERSION_SUFFIX = re.compile(r"_v(\d+)$")


def load_prompt(name: str) -> tuple[str, str]:
    """Load a prompt asset by name (without extension), e.g. "system_v1".

    Returns (text, prompt_version) where prompt_version is derived from the
    filename's version suffix (e.g. "system_v1" -> "v1").
    """
    match = _VERSION_SUFFIX.search(name)
    if match is None:
        raise ValueError(f"prompt name {name!r} has no _v<N> version suffix")
    prompt_version = f"v{match.group(1)}"

    path = _PROMPTS_DIR / f"{name}.md"
    text = path.read_text(encoding="utf-8")
    return text, prompt_version
