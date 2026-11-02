from __future__ import annotations

from emporio_agent.bootstrap import Application


def test_retrieves_right_of_withdrawal(application: Application) -> None:
    result = application.tools.policies.search(
        "Posso devolver uma compra online por arrependimento?"
    )

    assert result.found is True
    assert result.evidences
    assert result.evidences[0].section_number == "4.1"
    assert result.evidences[0].page_start == 4


def test_retrieves_store_hours(application: Application) -> None:
    result = application.tools.policies.search("Qual é o horário de funcionamento?")

    assert result.found is True
    assert result.evidences[0].section_number == "2"


def test_unknown_policy_has_no_evidence(application: Application) -> None:
    result = application.tools.policies.search("criptomoeda espacial interplanetária")

    assert result.found is False
    assert result.evidences == []
