from __future__ import annotations

from emporio_agent.bootstrap import Application


def test_order_requires_matching_customer_identifier(application: Application) -> None:
    invalid = application.tools.orders.get_verified(1, "pessoa.errada@example.com")
    valid = application.tools.orders.get_verified(1, "pedro.oliveira@jmail.com")

    assert invalid is None
    assert valid is not None
    assert valid.order_id == 1
    assert valid.status == "delivered"
    assert valid.tracking_code == "BRAB1234567BR"


def test_order_accepts_normalized_phone(application: Application) -> None:
    order = application.tools.orders.get_verified(1, "67984321098")

    assert order is not None
    assert order.order_id == 1
