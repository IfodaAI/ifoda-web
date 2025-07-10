from typing import Tuple, Dict, Optional

from app.models import OrderItems, Order
from payme.utils.get_params import get_params
from payme.serializers.payme_transaction_serializer import PaymeTransactionSerializer

class CheckPerformTransaction:
    def __call__(self, params: dict) -> Tuple[Optional[None], Dict[str, Dict[str, bool]]]:
        serializer = PaymeTransactionSerializer(
            data=get_params(params)
        )
        serializer.is_valid(raise_exception=True)
        order_id = serializer.validated_data.get("order_id")
        order = Order.objects.get(id=order_id)
        items = []
        order_items = OrderItems.objects.filter(order__id=order_id)

        for item in order_items:
            items.append({
                "discount": 0,
                "title": item.pills.name,
                "price": float(item.pills.price) * 100,
                "count": int(item.quantity),
                "code": item.pills.spic,
                "vat_percent": 12,
                "package_code": item.pills.package_code
            })

        if order.delivery_method == 'DELIVERY':
            items.append({
                "discount": 0,
                "title": "Доставка",
                "price": float(order.delivery_price) * 100,
                "count": 1,
                "code": "10112006002000000",
                "vat_percent": 12,
                "package_code": "1542432"
            })

        response = {
            "result": {
                "allow": True,
                "detail": {
                    "receipt_type": 0,
                    "items": items,
                    }
                }
            }

        return None, response
