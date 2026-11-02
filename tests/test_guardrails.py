from __future__ import annotations

import pytest

from emporio_agent.agent import AgentError, EmporioAgent
from emporio_agent.models import EvidenceRef, GroundedResponse


def test_factual_question_requires_evidence() -> None:
    response = GroundedResponse(
        answer="O produto custa R$ 100,00.",
        skill="preco_promocao_pagamento",
        evidence_refs=[],
    )

    with pytest.raises(AgentError, match="exige evidência"):
        EmporioAgent._validate_grounding(response, {}, "Quanto custa o produto?")


def test_rejects_unknown_evidence_reference() -> None:
    reference = EvidenceRef(
        source_type="tool",
        source_id="call-inexistente",
        tool_call_id="call-inexistente",
    )
    response = GroundedResponse(
        answer="Informação consultada.",
        skill="detalhes_e_comparacao",
        evidence_refs=[reference],
    )

    with pytest.raises(AgentError, match="Evidência inexistente"):
        EmporioAgent._validate_grounding(response, {}, "Qual é o estoque?")


def test_accepts_reference_from_current_turn() -> None:
    reference = EvidenceRef(
        source_type="tool",
        source_id="call-product",
        tool_call_id="call-product",
    )
    response = GroundedResponse(
        answer="O produto foi consultado.",
        skill="detalhes_e_comparacao",
        evidence_refs=[reference],
    )

    EmporioAgent._validate_grounding(
        response,
        {"call-product": reference},
        "O produto está disponível?",
    )


def test_assistant_tool_message_keeps_provider_extra_content() -> None:
    class Function:
        def __init__(self) -> None:
            self.name = "search_products"
            self.arguments = {"category": "Guitarras"}

    class Call:
        def __init__(self) -> None:
            self.id = "call-1"
            self.function = Function()
            self.type = "function"
            self.extra_content = {"google": {"thought_signature": "abc"}}

    class Message:
        def __init__(self) -> None:
            self.content = None
            self.tool_calls = [Call()]

        def model_dump(self, exclude_none: bool = False) -> dict:
            return {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {
                            "name": "search_products",
                            "arguments": {"category": "Guitarras"},
                        },
                        "extra_content": {"google": {"thought_signature": "abc"}},
                    }
                ],
            }

    payload = EmporioAgent._assistant_tool_message(Message())

    assert payload["tool_calls"][0]["extra_content"]["google"]["thought_signature"] == "abc"
    assert payload["tool_calls"][0]["function"]["arguments"] == '{"category": "Guitarras"}'


def test_parses_grounded_response_from_markdown_json() -> None:
    content = """```json
    {
      "answer": "Temos cinco guitarras disponíveis.",
      "skill": "descoberta_de_instrumentos",
      "evidence_refs": [],
      "requires_human": false,
      "limitation": null
    }
    ```"""

    response = EmporioAgent._parse_grounded_response(content)

    assert response.skill == "descoberta_de_instrumentos"
    assert "guitarras" in response.answer


def test_parses_plain_text_when_schema_is_optional() -> None:
    reference = EvidenceRef(
        source_type="tool",
        source_id="call-search",
        tool_call_id="call-search",
    )

    response = EmporioAgent._parse_grounded_response(
        "Temos cinco guitarras disponíveis.",
        allowed_evidence={"call-search": reference},
        require_schema=False,
    )

    assert "guitarras" in response.answer
    assert response.evidence_refs[0].source_id == "call-search"


def test_history_is_limited_and_roles_are_filtered() -> None:
    history = [
        {"role": "system", "content": "não permitido"},
        *[
            {"role": "user" if index % 2 == 0 else "assistant", "content": str(index)}
            for index in range(20)
        ],
    ]

    safe = EmporioAgent._safe_history(history)

    assert len(safe) == 12
    assert all(item["role"] in {"user", "assistant"} for item in safe)
    assert safe[0]["content"] == "8"
