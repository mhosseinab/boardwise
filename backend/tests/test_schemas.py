from app.schemas import (
    BoardCard,
    ChatRequest,
    ChatResponse,
    CompatibilityResult,
    SpecTable,
    ToolCall,
)


def make_board_card(board_id: str = "aquara-atlas-12") -> BoardCard:
    return BoardCard(
        id=board_id,
        brand="Aquara",
        model="Atlas 12'0\"",
        length_ft=12.0,
        width_in=32.0,
        thickness_in=6.0,
        volume_l=320.0,
        max_rider_weight_kg=140.0,
        recommended_psi=15,
        max_psi=18,
        board_type="touring",
        skill_level="intermediate",
        fin_box="US-box",
        valve_type="H3",
        board_weight_kg=11.5,
        price_usd=899.0,
        best_for=["flatwater", "touring"],
        image_url="/assets/placeholders/touring.svg",
        is_mock=True,
    )


def make_spec_table() -> SpecTable:
    return SpecTable(
        title="Touring boards compared",
        columns=["Model", "Length (ft)", "Capacity (kg)"],
        rows=[
            ["Aquara Atlas 12'0\"", "12.0", "140.0"],
            ["Riptide Tourer 11'6\"", "11.5", "120.0"],
        ],
        board_ids=["aquara-atlas-12", "riptide-tourer-11-6"],
    )


def make_compatibility_result() -> CompatibilityResult:
    return CompatibilityResult(
        board_id="aquara-atlas-12",
        accessory_id="fjord-glide-fin",
        compatible=True,
        reason="Fin box types match (US-box).",
        caveats=[],
    )


def make_tool_call() -> ToolCall:
    return ToolCall(
        name="get_board",
        args={"board_id": "aquara-atlas-12"},
        result_summary="Returned Aquara Atlas 12'0\" spec row.",
        latency_ms=12,
    )


def test_board_card_round_trip() -> None:
    card = make_board_card()
    assert BoardCard.model_validate(card.model_dump()) == card


def test_board_card_from_attributes_object() -> None:
    class FakeOrmRow:
        def __init__(self) -> None:
            self.id = "aquara-atlas-12"
            self.brand = "Aquara"
            self.model = "Atlas 12'0\""
            self.length_ft = 12.0
            self.width_in = 32.0
            self.thickness_in = 6.0
            self.volume_l = 320.0
            self.max_rider_weight_kg = 140.0
            self.recommended_psi = 15
            self.max_psi = 18
            self.board_type = "touring"
            self.skill_level = "intermediate"
            self.fin_box = "US-box"
            self.valve_type = "H3"
            self.board_weight_kg = 11.5
            self.price_usd = 899.0
            self.best_for = ["flatwater", "touring"]
            self.image_url = "/assets/placeholders/touring.svg"
            self.is_mock = True

    card = BoardCard.model_validate(FakeOrmRow())
    assert card == make_board_card()


def test_spec_table_round_trip() -> None:
    table = make_spec_table()
    assert SpecTable.model_validate(table.model_dump()) == table


def test_compatibility_result_round_trip() -> None:
    result = make_compatibility_result()
    assert CompatibilityResult.model_validate(result.model_dump()) == result


def test_compatibility_result_caveats_default_empty() -> None:
    result = CompatibilityResult(
        board_id="aquara-atlas-12",
        accessory_id="fjord-glide-fin",
        compatible=False,
        reason="Fin box mismatch.",
    )
    assert result.caveats == []


def test_tool_call_round_trip() -> None:
    call = make_tool_call()
    assert ToolCall.model_validate(call.model_dump()) == call


def test_chat_request_round_trip_with_history() -> None:
    request = ChatRequest(
        message="Is the Fjord Glide fin compatible with the Aquara Atlas 12'0\"?",
        history=[{"role": "user", "content": "hi"}],
    )
    assert ChatRequest.model_validate(request.model_dump()) == request


def test_chat_request_history_omitted_defaults_none() -> None:
    request = ChatRequest(message="hello")
    assert request.history is None


def test_chat_response_refused_defaults_false() -> None:
    response = ChatResponse(answer="Here's what I found.", prompt_version="v1")
    assert response.refused is False
    assert response.cards == []
    assert response.tables == []
    assert response.compatibility == []
    assert response.tools_used == []


def test_chat_response_full_nested_round_trip() -> None:
    response = ChatResponse(
        answer="The Aquara Atlas 12'0\" and Riptide Tourer 11'6\" compared.",
        cards=[make_board_card(), make_board_card("riptide-tourer-11-6")],
        tables=[make_spec_table()],
        compatibility=[make_compatibility_result()],
        tools_used=[make_tool_call()],
        refused=False,
        prompt_version="v1",
    )
    round_tripped = ChatResponse.model_validate(response.model_dump())
    assert round_tripped == response


def test_chat_response_refusal_shape() -> None:
    response = ChatResponse(
        answer="I only cover paddleboards and gear — ask me about SUP instead!",
        refused=True,
        prompt_version="v1",
    )
    assert response.refused is True
    assert response.tools_used == []
