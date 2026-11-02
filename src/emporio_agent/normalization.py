from __future__ import annotations

import re
import unicodedata
from decimal import ROUND_HALF_UP, Decimal

_NON_WORD = re.compile(r"[^\w\s]")
_MULTISPACE = re.compile(r"\s+")
_PHONE_DIGITS = re.compile(r"\D")


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = _NON_WORD.sub(" ", value.casefold())
    return _MULTISPACE.sub(" ", value).strip()


def normalize_email(value: str) -> str:
    return value.strip().casefold()


def normalize_phone(value: str) -> str:
    return _PHONE_DIGITS.sub("", value)


def normalize_customer_identifier(value: str) -> tuple[str, str]:
    if "@" in value:
        return "email", normalize_email(value)
    return "phone", normalize_phone(value)


def money(value: Decimal | str | float | int) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
