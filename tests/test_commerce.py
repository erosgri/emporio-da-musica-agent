from __future__ import annotations

from decimal import Decimal

from emporio_agent.bootstrap import Application


def test_active_promotion_is_not_combined_with_pix(application: Application) -> None:
    options = application.tools.commerce.calculate_purchase_options(127)

    assert options is not None
    assert options.list_price_brl == Decimal("359.00")
    assert options.active_discount_percent == Decimal("10")
    assert options.promotional_price_brl == Decimal("323.10")
    assert options.pix_price_brl == Decimal("323.10")
    assert options.pix_discount_applied is False


def test_pix_discount_applies_without_promotion(application: Application) -> None:
    options = application.tools.commerce.calculate_purchase_options(95)

    assert options is not None
    assert options.promotional_price_brl is None
    assert options.pix_price_brl == Decimal("2089.05")
    assert options.pix_discount_applied is True


def test_installment_rules(application: Application) -> None:
    assert application.tools.commerce._max_installments(Decimal("49.99")) == 1
    assert application.tools.commerce._max_installments(Decimal("50.00")) == 3
    assert application.tools.commerce._max_installments(Decimal("480.00")) == 6
    assert application.tools.commerce._max_installments(Decimal("1200.00")) == 12
