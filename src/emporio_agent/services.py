from __future__ import annotations

from decimal import Decimal

from emporio_agent.models import PaymentOptions
from emporio_agent.normalization import money
from emporio_agent.repositories import ProductRepository


class CommerceService:
    def __init__(self, products: ProductRepository) -> None:
        self.products = products

    def calculate_purchase_options(self, product_id: int) -> PaymentOptions | None:
        product = self.products.get_by_id(product_id)
        if product is None:
            return None

        promotional_price = product.promotional_price_brl
        card_price = promotional_price or product.price_brl
        if promotional_price is not None:
            pix_price = promotional_price
            pix_discount_applied = False
        else:
            pix_price = money(product.price_brl * Decimal("0.95"))
            pix_discount_applied = True

        max_installments = self._max_installments(card_price)
        installment_value = money(card_price / Decimal(max_installments))
        return PaymentOptions(
            product_id=product.product_id,
            product_name=product.name,
            list_price_brl=product.price_brl,
            active_discount_percent=product.active_discount_percent,
            promotional_price_brl=promotional_price,
            pix_price_brl=pix_price,
            pix_discount_applied=pix_discount_applied,
            card_price_brl=card_price,
            max_installments=max_installments,
            installment_value_brl=installment_value,
            combinable_pix_and_card=card_price > Decimal("2000"),
        )

    @staticmethod
    def _max_installments(total: Decimal) -> int:
        for installments in range(12, 0, -1):
            installment_value = total / Decimal(installments)
            if installments >= 7 and installment_value >= Decimal("100"):
                return installments
            if 4 <= installments <= 6 and installment_value >= Decimal("80"):
                return installments
            if 2 <= installments <= 3 and total >= Decimal("50"):
                return installments
            if installments == 1:
                return 1
        return 1
