from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from emporio_agent.models import ProductDetail
from emporio_agent.policy import PolicyRetriever
from emporio_agent.repositories import OrderRepository, ProductRepository
from emporio_agent.services import CommerceService


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchProductsInput(ToolInput):
    query: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)
    strings: Literal["nylon", "steel"] | None = None
    electronics: bool | None = None
    available_only: bool = True
    limit: int = Field(default=5, ge=1, le=10)

    @model_validator(mode="after")
    def validate_price_range(self) -> SearchProductsInput:
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("min_price não pode ser maior que max_price")
        return self


class GetProductInput(ToolInput):
    product_id: int | None = Field(default=None, gt=0)
    product_name: str | None = Field(default=None, min_length=2, max_length=200)

    @model_validator(mode="after")
    def validate_identifier(self) -> GetProductInput:
        if (self.product_id is None) == (self.product_name is None):
            raise ValueError("Informe exatamente product_id ou product_name")
        return self


class CalculatePurchaseOptionsInput(ToolInput):
    product_id: int = Field(gt=0)


class GetOrderStatusInput(ToolInput):
    order_id: int = Field(gt=0)
    customer_identifier: str = Field(min_length=5, max_length=254)


class SearchStorePolicyInput(ToolInput):
    topic: str = Field(min_length=3, max_length=500)
    limit: int = Field(default=3, ge=1, le=5)


class GetStoreInformationInput(ToolInput):
    field: Literal["address", "hours", "phone", "whatsapp", "email", "catalog_scope"]


STORE_INFORMATION: dict[str, dict[str, str]] = {
    "address": {
        "value": "Rua 14 de Maio, 3200 — Centro, Campo Grande - MS, CEP 79202-333",
        "reference": "Política 1.2, página 2",
    },
    "hours": {
        "value": (
            "Segunda a sexta, das 09:00 às 18:00; sábado, das 09:00 às 13:00; "
            "domingo e feriados, fechado."
        ),
        "reference": "Política 2, página 2",
    },
    "phone": {
        "value": "(67) 3341-4444",
        "reference": "Política 1.2, página 2",
    },
    "whatsapp": {
        "value": "(67) 3321-4500",
        "reference": "Política 7, página 6",
    },
    "email": {
        "value": "contato@emporiodamusica.com.br",
        "reference": "Capa do manual, página 1",
    },
    "catalog_scope": {
        "value": (
            "A loja trabalha exclusivamente com instrumentos musicais e não comercializa "
            "acessórios, amplificadores, pedais, cabos, cases, palhetas ou cordas."
        ),
        "reference": "Política 1, página 2",
    },
}


TOOL_MODELS: dict[str, type[ToolInput]] = {
    "search_products": SearchProductsInput,
    "get_product": GetProductInput,
    "calculate_purchase_options": CalculatePurchaseOptionsInput,
    "get_order_status": GetOrderStatusInput,
    "search_store_policy": SearchStorePolicyInput,
    "get_store_information": GetStoreInformationInput,
}

TOOL_DESCRIPTIONS = {
    "search_products": (
        "Busca instrumentos no catálogo usando filtros. Use para recomendações e listas. "
        "Por padrão retorna somente itens realmente disponíveis."
    ),
    "get_product": (
        "Obtém detalhes atuais de um instrumento por ID ou nome. Use antes de afirmar "
        "preço, estoque, especificações ou promoção."
    ),
    "calculate_purchase_options": (
        "Calcula preço promocional, PIX e parcelamento de um produto pelas regras da loja."
    ),
    "get_order_status": (
        "Consulta um pedido após validar número e e-mail ou telefone do cliente. "
        "Nunca use nome como identificador."
    ),
    "search_store_policy": (
        "Pesquisa o manual para trocas, devoluções, garantia, frete, pagamento, "
        "promoções, privacidade e demais políticas."
    ),
    "get_store_information": (
        "Obtém endereço, horário, telefone, WhatsApp, e-mail ou escopo do catálogo."
    ),
}


class ToolRegistry:
    def __init__(
        self,
        products: ProductRepository,
        orders: OrderRepository,
        commerce: CommerceService,
        policies: PolicyRetriever,
    ) -> None:
        self.products = products
        self.orders = orders
        self.commerce = commerce
        self.policies = policies

    def openai_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": TOOL_DESCRIPTIONS[name],
                    "parameters": model.model_json_schema(),
                },
            }
            for name, model in TOOL_MODELS.items()
        ]

    def execute(self, name: str, arguments: dict[str, Any], *, call_id: str) -> dict[str, Any]:
        model = TOOL_MODELS.get(name)
        if model is None:
            raise ValueError("Ferramenta não autorizada.")
        validated = model.model_validate(arguments)

        if isinstance(validated, SearchProductsInput):
            results = self.products.search(
                query=validated.query,
                category=validated.category,
                min_price=(
                    Decimal(str(validated.min_price)) if validated.min_price is not None else None
                ),
                max_price=(
                    Decimal(str(validated.max_price)) if validated.max_price is not None else None
                ),
                strings=validated.strings,
                electronics=validated.electronics,
                available_only=validated.available_only,
                limit=validated.limit,
            )
            return self._with_evidence(
                call_id,
                {
                    "found": bool(results),
                    "count": len(results),
                    "products": [item.model_dump(mode="json") for item in results],
                },
            )

        if isinstance(validated, GetProductInput):
            if validated.product_id is not None:
                product = self.products.get_by_id(validated.product_id)
                return self._with_evidence(
                    call_id,
                    {
                        "found": product is not None,
                        "product": product.model_dump(mode="json") if product else None,
                    },
                )
            matches = self.products.find_by_name(validated.product_name or "")
            exact = self._exact_name_match(matches, validated.product_name or "")
            if exact is not None:
                return self._with_evidence(
                    call_id,
                    {"found": True, "ambiguous": False, "product": exact.model_dump(mode="json")},
                )
            return self._with_evidence(
                call_id,
                {
                    "found": bool(matches),
                    "ambiguous": len(matches) > 1,
                    "matches": [item.model_dump(mode="json") for item in matches],
                },
            )

        if isinstance(validated, CalculatePurchaseOptionsInput):
            options = self.commerce.calculate_purchase_options(validated.product_id)
            return self._with_evidence(
                call_id,
                {
                    "found": options is not None,
                    "options": options.model_dump(mode="json") if options else None,
                },
            )

        if isinstance(validated, GetOrderStatusInput):
            order = self.orders.get_verified(validated.order_id, validated.customer_identifier)
            return self._with_evidence(
                call_id,
                {
                    "verified": order is not None,
                    "message": (
                        "Pedido validado."
                        if order is not None
                        else "Não foi possível validar o pedido com os dados informados."
                    ),
                    "order": order.model_dump(mode="json") if order else None,
                },
            )

        if isinstance(validated, SearchStorePolicyInput):
            result = self.policies.search(validated.topic, limit=validated.limit)
            payload = result.model_dump(mode="json")
            payload["_evidence_refs"] = [
                {
                    "source_type": "policy",
                    "source_id": evidence.chunk_id,
                    "tool_call_id": call_id,
                    "chunk_id": evidence.chunk_id,
                }
                for evidence in result.evidences
            ]
            return payload

        if isinstance(validated, GetStoreInformationInput):
            return self._with_evidence(
                call_id,
                {"field": validated.field, **STORE_INFORMATION[validated.field]},
            )

        raise TypeError("Contrato de ferramenta não implementado.")

    @staticmethod
    def _exact_name_match(
        matches: list[ProductDetail], requested_name: str
    ) -> ProductDetail | None:
        requested = requested_name.strip().casefold()
        return next((item for item in matches if item.name.casefold() == requested), None)

    @staticmethod
    def _with_evidence(call_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        payload["_evidence_refs"] = [
            {
                "source_type": "tool",
                "source_id": call_id,
                "tool_call_id": call_id,
                "chunk_id": None,
            }
        ]
        return payload
