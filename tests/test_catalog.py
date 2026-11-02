from __future__ import annotations

from decimal import Decimal

from emporio_agent.bootstrap import Application


def test_search_only_returns_available_products(application: Application) -> None:
    products = application.tools.products.search(
        category="Violões",
        max_price=Decimal("1000"),
        available_only=True,
        limit=20,
    )

    assert products
    assert all(product.available for product in products)
    assert all(product.price_brl <= Decimal("1000") for product in products)
    assert all(product.product_id != 96 for product in products)


def test_product_with_zero_stock_is_unavailable(application: Application) -> None:
    product = application.tools.products.get_by_id(96)

    assert product is not None
    assert product.status == "active"
    assert product.stock_quantity == 0
    assert product.available is False


def test_coming_soon_product_is_unavailable(application: Application) -> None:
    product = application.tools.products.get_by_id(130)

    assert product is not None
    assert product.stock_quantity > 0
    assert product.status == "coming_soon"
    assert product.available is False
