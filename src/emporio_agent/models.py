from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ProductSummary(BaseModel):
    product_id: int
    name: str
    category: str
    price_brl: Decimal
    stock_quantity: int
    status: str
    available: bool
    active_discount_percent: Decimal | None = None
    promotional_price_brl: Decimal | None = None


class ProductDetail(ProductSummary):
    description: str
    specs: dict[str, Any]
    promotion_description: str | None = None


class PaymentOptions(BaseModel):
    product_id: int
    product_name: str
    list_price_brl: Decimal
    active_discount_percent: Decimal | None = None
    promotional_price_brl: Decimal | None = None
    pix_price_brl: Decimal
    pix_discount_applied: bool
    card_price_brl: Decimal
    max_installments: int
    installment_value_brl: Decimal
    combinable_pix_and_card: bool


class OrderItem(BaseModel):
    product_id: int
    product_name: str
    quantity: int


class OrderStatus(BaseModel):
    order_id: int
    order_date: str
    status: str
    total_brl: Decimal
    payment_method: str
    tracking_code: str | None = None
    estimated_delivery: str | None = None
    notes: str | None = None
    items: list[OrderItem]


class PolicyChunk(BaseModel):
    chunk_id: str
    document_id: str
    source_file: str
    document_version: str
    section_number: str
    section_title: str
    page_start: int
    page_end: int
    content: str
    normalized_content: str
    checksum: str


class PolicyEvidence(BaseModel):
    chunk_id: str
    section_number: str
    section_title: str
    page_start: int
    page_end: int
    excerpt: str
    score: float
    source_file: str
    document_version: str


class PolicySearchResult(BaseModel):
    found: bool
    query: str
    evidences: list[PolicyEvidence]


class EvidenceRef(StrictModel):
    source_type: Literal["tool", "policy"]
    source_id: str
    tool_call_id: str | None = None
    chunk_id: str | None = None


class GroundedResponse(StrictModel):
    answer: str = Field(min_length=1, max_length=4000)
    skill: str = Field(min_length=1, max_length=100)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    requires_human: bool = False
    limitation: str | None = Field(default=None, max_length=500)
