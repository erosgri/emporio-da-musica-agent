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
