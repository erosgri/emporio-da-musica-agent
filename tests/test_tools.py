from __future__ import annotations

from emporio_agent.bootstrap import Application


def test_search_tool_returns_evidence(application: Application) -> None:
    result = application.tools.execute(
        "search_products",
        {"category": "Violões", "max_price": 1000, "limit": 3},
        call_id="call-catalog",
    )

    assert result["found"] is True
    assert result["count"] == 3
    assert result["_evidence_refs"][0]["source_id"] == "call-catalog"


def test_policy_tool_returns_chunk_references(application: Application) -> None:
    result = application.tools.execute(
        "search_store_policy",
        {"topic": "garantia legal", "limit": 2},
        call_id="call-policy",
    )

    assert result["found"] is True
    assert result["_evidence_refs"]
    assert result["_evidence_refs"][0]["source_type"] == "policy"


def test_order_tool_does_not_expose_customer_data(application: Application) -> None:
    result = application.tools.execute(
        "get_order_status",
        {"order_id": 1, "customer_identifier": "pedro.oliveira@jmail.com"},
        call_id="call-order",
    )

    serialized = str(result)
    assert result["verified"] is True
    assert "Pedro Henrique" not in serialized
    assert "pedro.oliveira" not in serialized
    assert "(67)" not in serialized
