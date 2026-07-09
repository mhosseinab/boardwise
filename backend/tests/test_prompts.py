from app.prompts.loader import load_prompt


def test_system_prompt_loads_nonempty_v1() -> None:
    text, version = load_prompt("system_v1")
    assert text.strip() != ""
    assert version == "v1"


def test_tools_prompt_loads_nonempty_v1() -> None:
    text, version = load_prompt("tools_v1")
    assert text.strip() != ""
    assert version == "v1"


def test_system_prompt_instructs_missing_spec_phrase() -> None:
    text, _ = load_prompt("system_v1")
    assert "I don't have that spec" in text
