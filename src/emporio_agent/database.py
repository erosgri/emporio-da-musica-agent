from __future__ import annotations

import csv
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from emporio_agent.config import Settings
from emporio_agent.normalization import normalize_email, normalize_phone, normalize_text

CSV_SUFFIXES = {
    "categories": "categories.csv",
    "products": "products.csv",
    "promotions": "promotions.csv",
    "customers": "customers.csv",
    "orders": "orders.csv",
    "order_items": "order_items.csv",
}


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE categories (
    category_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    price_brl TEXT NOT NULL,
    name TEXT NOT NULL,
    search_text TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(category_id),
    description TEXT NOT NULL,
    stock_quantity INTEGER NOT NULL CHECK (stock_quantity >= 0),
    status TEXT NOT NULL CHECK (status IN ('active', 'discontinued', 'coming_soon')),
    specs TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE promotions (
    promotion_id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    discount_percent TEXT NOT NULL,
    description TEXT NOT NULL,
    is_active INTEGER NOT NULL CHECK (is_active IN (0, 1))
);

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    normalized_phone TEXT NOT NULL,
    email TEXT NOT NULL,
    normalized_email TEXT NOT NULL,
    city TEXT NOT NULL
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled')
    ),
    total_brl TEXT NOT NULL,
    payment_method TEXT NOT NULL,
    tracking_code TEXT,
    estimated_delivery TEXT,
    notes TEXT
);

CREATE TABLE order_items (
    order_id INTEGER NOT NULL REFERENCES orders(order_id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    PRIMARY KEY (order_id, product_id)
);

CREATE INDEX idx_products_search ON products(search_text);
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_availability ON products(status, stock_quantity);
CREATE INDEX idx_promotions_product_active ON promotions(product_id, is_active);
CREATE INDEX idx_orders_customer ON orders(customer_id);
"""


def _find_csv(artifacts_dir: Path, suffix: str) -> Path:
    matches = sorted(artifacts_dir.glob(f"*{suffix}"))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"Esperado exatamente um arquivo terminado em {suffix!r}; encontrados: {matches}"
        )
    return matches[0]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _optional(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def initialize_database(settings: Settings, *, force: bool = False) -> Path:
    database_path = settings.database_path
    if database_path.exists() and not force:
        return database_path

    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    temporary_path = database_path.with_suffix(".tmp")
    temporary_path.unlink(missing_ok=True)

    sources = {
        key: _find_csv(settings.artifacts_dir, suffix) for key, suffix in CSV_SUFFIXES.items()
    }

    connection = sqlite3.connect(temporary_path)
    try:
        connection.executescript(SCHEMA)
        with connection:
            for row in _read_csv(sources["categories"]):
                connection.execute(
                    "INSERT INTO categories VALUES (?, ?, ?, ?)",
                    (
                        int(row["category_id"]),
                        row["name"].strip(),
                        normalize_text(row["name"]),
                        row["description"].strip(),
                    ),
                )

            for row in _read_csv(sources["products"]):
                specs = json.loads(row["specs"])
                search_text = normalize_text(
                    f"{row['name']} {row['description']} {' '.join(map(str, specs.values()))}"
                )
                connection.execute(
                    "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        int(row["product_id"]),
                        row["price_brl"],
                        row["name"].strip(),
                        search_text,
                        int(row["category_id"]),
                        row["description"].strip(),
                        int(row["stock_quantity"]),
                        row["status"].strip(),
                        json.dumps(specs, ensure_ascii=False, separators=(",", ":")),
                        row["created_at"].strip(),
                    ),
                )

            for row in _read_csv(sources["promotions"]):
                connection.execute(
                    "INSERT INTO promotions VALUES (?, ?, ?, ?, ?)",
                    (
                        int(row["promotion_id"]),
                        int(row["product_id"]),
                        row["discount_percent"],
                        row["description"].strip(),
                        int(row["is_active"]),
                    ),
                )

            for row in _read_csv(sources["customers"]):
                connection.execute(
                    "INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        int(row["customer_id"]),
                        row["name"].strip(),
                        row["phone"].strip(),
                        normalize_phone(row["phone"]),
                        row["email"].strip(),
                        normalize_email(row["email"]),
                        row["city"].strip(),
                    ),
                )

            for row in _read_csv(sources["orders"]):
                connection.execute(
                    "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        int(row["order_id"]),
                        int(row["customer_id"]),
                        row["order_date"].strip(),
                        row["status"].strip(),
                        row["total_brl"],
                        row["payment_method"].strip(),
                        _optional(row["tracking_code"]),
                        _optional(row["estimated_delivery"]),
                        _optional(row["notes"]),
                    ),
                )

            for row in _read_csv(sources["order_items"]):
                connection.execute(
                    "INSERT INTO order_items VALUES (?, ?, ?)",
                    (
                        int(row["order_id"]),
                        int(row["quantity"]),
                        int(row["product_id"]),
                    ),
                )

        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise ValueError(f"Falhas de integridade referencial: {violations}")
    except Exception:
        connection.close()
        temporary_path.unlink(missing_ok=True)
        raise
    else:
        connection.close()

    temporary_path.replace(database_path)
    return database_path


@contextmanager
def readonly_connection(database_path: Path) -> Iterator[sqlite3.Connection]:
    uri = f"{database_path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()
