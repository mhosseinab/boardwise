from app.agent.guardrails import GroundingResult, validate_grounding

AQUARA_ATLAS = {
    "id": "aquara-atlas-12",
    "brand": "Aquara",
    "model": "Atlas 12'0\"",
    "length_ft": 12.0,
    "width_in": 32.0,
    "thickness_in": 6.0,
    "volume_l": 149.6,
    "max_rider_weight_kg": 100.0,
    "recommended_psi": 15,
    "max_psi": 18,
    "board_type": "touring",
    "skill_level": "intermediate",
    "fin_box": "US-box",
    "valve_type": "H3",
    "board_weight_kg": 9.5,
    "price_usd": 899.0,
    "best_for": ["touring", "flatwater"],
    "image_url": "/assets/placeholders/touring.svg",
    "is_mock": True,
}


def test_fully_grounded_answer_unchanged() -> None:
    answer = (
        "The Aquara Atlas holds 149.6 L of volume and costs $899.0. "
        "Recommended pressure is 15 psi."
    )
    result = validate_grounding(answer, [AQUARA_ATLAS])
    assert result == GroundingResult(
        clean_answer=answer, stripped_claims=[], grounded=True
    )


def test_invented_psi_stripped() -> None:
    answer = "Inflate this board to 45 psi for best performance."
    result = validate_grounding(answer, [AQUARA_ATLAS])
    assert result.grounded is False
    assert "45 psi" in result.stripped_claims
    assert "45 psi" not in result.clean_answer
    assert "I don't have that spec in my catalog." == result.clean_answer


def test_kg_value_stated_in_lbs_passes_via_conversion() -> None:
    answer = "This board supports riders up to 220 lbs."
    result = validate_grounding(answer, [AQUARA_ATLAS])
    assert result == GroundingResult(
        clean_answer=answer, stripped_claims=[], grounded=True
    )


def test_about_150_l_passes_rounding_tolerance_against_149_6() -> None:
    answer = "The tank volume is about 150 L."
    result = validate_grounding(answer, [AQUARA_ATLAS])
    assert result == GroundingResult(
        clean_answer=answer, stripped_claims=[], grounded=True
    )


def test_invented_price_stripped_while_grounded_price_survives() -> None:
    answer = "The Aquara Atlas costs $899.0. The optional Riptide fin costs $999.0."
    result = validate_grounding(answer, [AQUARA_ATLAS])
    assert result.grounded is False
    assert result.stripped_claims == ["$999.0"]
    assert "The Aquara Atlas costs $899.0." in result.clean_answer
    assert "$999.0" not in result.clean_answer
    assert "I don't have that spec in my catalog." in result.clean_answer


def test_empty_tool_results_strips_all_spec_claims_and_not_grounded() -> None:
    answer = "This board holds 45 psi and costs $899."
    result = validate_grounding(answer, [])
    assert result.grounded is False
    assert result.stripped_claims == ["45 psi", "$899"]
    assert result.clean_answer == "I don't have that spec in my catalog."


def test_grounded_board_name_with_embedded_digits_survives() -> None:
    answer = "The Aquara Atlas 12'0\" is a great touring board."
    result = validate_grounding(answer, [AQUARA_ATLAS])
    assert result == GroundingResult(
        clean_answer=answer, stripped_claims=[], grounded=True
    )


def test_bare_count_is_never_treated_as_a_spec_claim() -> None:
    answer = "We found 2 boards that fit your rider profile."
    result = validate_grounding(answer, [])
    assert result == GroundingResult(
        clean_answer=answer, stripped_claims=[], grounded=True
    )


def test_multiple_sentences_each_evaluated_independently() -> None:
    answer = (
        "The Aquara Atlas is rated for 100 kg. "
        "It also comes in a lighter build rated at 999 kg."
    )
    result = validate_grounding(answer, [AQUARA_ATLAS])
    assert result.grounded is False
    assert result.stripped_claims == ["999 kg"]
    assert result.clean_answer == (
        "The Aquara Atlas is rated for 100 kg. I don't have that spec in my catalog."
    )


def test_nested_tool_results_are_walked_recursively() -> None:
    bundle = {
        "board": {"id": "zephyr-cruiser-11", "price_usd": 799.0, "is_mock": True},
        "paddle": {"id": "cascade-carbon-paddle", "price_usd": 149.0, "is_mock": True},
    }
    answer = "The Zephyr Cruiser is $799.0 and the Cascade paddle adds $149.0."
    result = validate_grounding(answer, [bundle])
    assert result == GroundingResult(
        clean_answer=answer, stripped_claims=[], grounded=True
    )


def test_no_numeric_claims_at_all_is_trivially_grounded() -> None:
    answer = "This is a great all-around board for beginners."
    result = validate_grounding(answer, [AQUARA_ATLAS])
    assert result == GroundingResult(
        clean_answer=answer, stripped_claims=[], grounded=True
    )


def test_feet_inches_claim_grounds_against_numeric_length_ft_without_name_match() -> (
    None
):
    answer = "This board measures 12'0\" from nose to tail."
    tool_result = {"id": "velocity-glide-12", "length_ft": 12.0, "is_mock": True}
    result = validate_grounding(answer, [tool_result])
    assert result == GroundingResult(
        clean_answer=answer, stripped_claims=[], grounded=True
    )


def test_invented_weight_does_not_false_positive_against_unrelated_pooled_numbers() -> (
    None
):
    # Regression guard: an invented weight claim must not accidentally match some other
    # field's number (or its unit conversion) that happens to be numerically close.
    answer = "This board weighs 50 kg fully rigged."
    fjord_board = {
        "id": "fjord-drift-10",
        "price_usd": 899.0,
        "thickness_in": 6.0,
        "is_mock": True,
    }
    result = validate_grounding(answer, [fjord_board])
    assert result.grounded is False
    assert result.stripped_claims == ["50 kg"]
    assert "50 kg" not in result.clean_answer
