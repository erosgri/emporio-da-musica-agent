from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from emporio_agent.database import readonly_connection
from emporio_agent.models import OrderItem, OrderStatus, ProductDetail, ProductSummary
from emporio_agent.normalization import money, normalize_customer_identifier, normalize_text

PRODUCT_SELECT = """
SELECT
    p.product_id,
    p.name,
    c.name AS category,
    p.price_brl,
    p.description,
    p.stock_quantity,
    p.status,
    p.specs,
    (
        SELECT pr.discount_percent
        FROM promotions pr
        WHERE pr.product_id = p.product_id AND pr.is_active = 1
        ORDER BY CAST(pr.discount_percent AS REAL) DESC, pr.promotion_id ASC
        LIMIT 1
    ) AS active_discount_percent,
    (
        SELECT pr.description
        FROM promotions pr
        WHERE pr.product_id = p.product_id AND pr.is_active = 1
        ORDER BY CAST(pr.discount_percent AS REAL) DESC, pr.promotion_id ASC
        LIMIT 1
    ) AS promotion_description
FROM products p
JOIN categories c ON c.category_id = p.category_id
"""


def _promotional_price(price: Decimal, discount: Decimal | None) -> Decimal | None:
    if discount is None:
        return None
    return money(price * (Decimal("1") - discount / Decimal("100")))


def _row_to_product(row: Any, *, detail: bool) -> ProductSummary | ProductDetail:
    price = money(row["price_brl"])
    discount = (
        Decimal(str(row["active_discount_percent"]))
        if row["active_discount_percent"] is not None
        else None
    )
    common: dict[str, Any] = {
        "product_id": row["product_id"],
        "name": row["name"],
        "category": row["category"],
        "price_brl": price,
        "stock_quantity": row["stock_quantity"],
        "status": row["status"],
        "available": row["status"] == "active" and row["stock_quantity"] > 0,
        "active_discount_percent": discount,
        "promotional_price_brl": _promotional_price(price, discount),
    }
    if not detail:
        return ProductSummary(**common)
    return ProductDetail(
        **common,
        description=row["description"],
        specs=json.loads(row["specs"]),
        promotion_description=row["promotion_description"],
    )


class ProductRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def search(
        self,
        *,
        query: str | None = None,
        category: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        strings: str | None = None,
        electronics: bool | None = None,
        available_only: bool = True,
        limit: int = 5,
    ) -> list[ProductSummary]:
        conditions: list[str] = []
        parameters: list[Any] = []

        if query:
            for token in normalize_text(query).split():
                conditions.append("p.search_text LIKE ?")
                parameters.append(f"%{token}%")
        if category:
            conditions.append("c.normalized_name LIKE ?")
            parameters.append(f"%{normalize_text(category)}%")
        if min_price is not None:
            conditions.append("CAST(p.price_brl AS REAL) >= ?")
            parameters.append(float(min_price))
        if max_price is not None:
            conditions.append("CAST(p.price_brl AS REAL) <= ?")
            parameters.append(float(max_price))
        if strings:
            conditions.append("json_extract(p.specs, '$.strings') = ?")
            parameters.append(strings)
        if electronics is not None:
            conditions.append("json_extract(p.specs, '$.electronics') = ?")
            parameters.append("yes" if electronics else "no")
        if available_only:
            conditions.extend(["p.status = 'active'", "p.stock_quantity > 0"])

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"{PRODUCT_SELECT} {where} ORDER BY CAST(p.price_brl AS REAL), p.product_id LIMIT ?"
        parameters.append(limit)
        with readonly_connection(self.database_path) as connection:
            rows = connection.execute(sql, parameters).fetchall()
        return [_row_to_product(row, detail=False) for row in rows]

    def get_by_id(self, product_id: int) -> ProductDetail | None:
        with readonly_connection(self.database_path) as connection:
            row = connection.execute(
                f"{PRODUCT_SELECT} WHERE p.product_id = ?", (product_id,)
            ).fetchone()
        if row is None:
            return None
        return _row_to_product(row, detail=True)  # type: ignore[return-value]

    def find_by_name(self, name: str, *, limit: int = 5) -> list[ProductDetail]:
        normalized = normalize_text(name)
        conditions = ["p.search_text LIKE ?" for _ in normalized.split()]
        parameters: list[Any] = [f"%{token}%" for token in normalized.split()]
        parameters.append(limit)
        where = " AND ".join(conditions) or "1 = 0"
        sql = (
            f"{PRODUCT_SELECT} WHERE {where} "
            "ORDER BY CASE WHEN p.search_text LIKE ? THEN 0 ELSE 1 END, p.product_id LIMIT ?"
        )
        parameters.insert(-1, f"{normalized}%")
        with readonly_connection(self.database_path) as connection:
            rows = connection.execute(sql, parameters).fetchall()
        return [_row_to_product(row, detail=True) for row in rows]  # type: ignore[misc]


class OrderRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def get_verified(self, order_id: int, customer_identifier: str) -> OrderStatus | None:
        identifier_type, normalized = normalize_customer_identifier(customer_identifier)
        if not normalized:
            return None
        identifier_column = (
            "c.normalized_email" if identifier_type == "email" else "c.normalized_phone"
        )
        sql = f"""
            SELECT o.*
            FROM orders o
            JOIN customers c ON c.customer_id = o.customer_id
            WHERE o.order_id = ? AND {identifier_column} = ?
        """
        with readonly_connection(self.database_path) as connection:
            order = connection.execute(sql, (order_id, normalized)).fetchone()
            if order is None:
                return None
            rows = connection.execute(
                """
                SELECT oi.product_id, p.name, oi.quantity
                FROM order_items oi
                JOIN products p ON p.product_id = oi.product_id
                WHERE oi.order_id = ?
                ORDER BY oi.product_id
                """,
                (order_id,),
            ).fetchall()

        return OrderStatus(
            order_id=order["order_id"],
            order_date=order["order_date"],
            status=order["status"],
            total_brl=money(order["total_brl"]),
            payment_method=order["payment_method"],
            tracking_code=order["tracking_code"],
            estimated_delivery=order["estimated_delivery"],
            notes=order["notes"],
            items=[
                OrderItem(
                    product_id=row["product_id"],
                    product_name=row["name"],
                    quantity=row["quantity"],
                )
                for row in rows
            ],
        )
